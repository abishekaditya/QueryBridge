#!/usr/bin/env python3
"""benchmark.py – GraphQL / SQLite vs. XSB micro-benchmark
========================================================

For each `schema.graphql` + `query.graphql` in the test folders, this script:

1. Runs GraphQL via Ariadne + SQLite and measures timing.
2. Generates XSB code (with and without demand) via `translate_graphql_to_xsb`,
   writes Prolog drivers, runs them in XSB, and measures timing.
3. Verifies that the outputs match between both XSB variants
   and compares counts with the SQLite path.

Usage:
```bash
pip install ariadne graphql-core sqlalchemy
python benchmark.py tests --runs 5 --xsb-path /usr/local/bin/xsb
```
"""

from __future__ import annotations
import argparse
import re
import subprocess
import time
import statistics
from pathlib import Path
from typing import Dict, List, Tuple

from graphql import (
    GraphQLList,
    GraphQLNonNull,
    GraphQLScalarType,
    build_ast_schema,
    graphql_sync,
    parse,
)
from sqlalchemy import Column, MetaData, Table, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.sql import alias
from ariadne import ObjectType, QueryType, gql, make_executable_schema

from cleanup import clean

try:
    from querybridge.translator import translate_graphql_to_xsb
except ImportError:
    from translator import translate_graphql_to_xsb


def unwrap(typ):
    while isinstance(typ, (GraphQLNonNull, GraphQLList)):
        typ = typ.of_type
    return typ


def is_scalar(typ) -> bool:
    return isinstance(unwrap(typ), GraphQLScalarType)


def returns_list(typ) -> bool:
    return (
        isinstance(typ, GraphQLList)
        or (
            isinstance(typ, GraphQLNonNull)
            and isinstance(typ.of_type, GraphQLList)
        )
    )


def load_facts(engine: Engine, facts_path: Path) -> Dict[str, Table]:
    """
    Parse `facts.P` with mixed arity, create tables, and insert rows.
    """
    metadata = MetaData()
    lines = [
        line.strip()
        for line in facts_path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("%")
    ]

    parsed: List[Tuple[str, List[str]]] = []
    pattern = re.compile(r"^(\w+)\((.*)\)\.$")
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        pred, blob = match.groups()
        parts = [part.strip().strip('"') for part in blob.split(",")]
        parsed.append((pred, parts))

    # determine maximum arity per predicate
    arity: Dict[str, int] = {}
    for pred, parts in parsed:
        arity[pred] = max(arity.get(pred, 0), len(parts))

    # create tables
    tables: Dict[str, Table] = {}
    for pred, n in arity.items():
        columns = [Column(f"arg{i+1}", Text) for i in range(n)]
        table = Table(pred, metadata, *columns)
        table.create(bind=engine)
        tables[pred] = table

    # insert rows, padding with None
    with engine.begin() as conn:
        for pred, parts in parsed:
            table = tables[pred]
            ncols = len(table.columns)
            padded = parts + [None] * (ncols - len(parts))
            conn.execute(table.insert().values({f"arg{i+1}": padded[i] for i in range(ncols)}))

    return tables


def make_root_resolver(obj_name: str, tables: Dict[str, Table]):
    base_name = f"{obj_name.lower()}_ext"

    def resolver(_, info, **kwargs):
        conn = info.context["conn"]
        tbls = info.context["tables"]
        if base_name not in tbls:
            return [] if returns_list(info.return_type) else None

        base_alias = alias(tbls[base_name], obj_name)
        conditions = []
        src = base_alias

        for key, val in kwargs.items():
            cand_names = [f"{obj_name.lower()}_{key}_ext", f"{key}_ext"]
            for cand in cand_names:
                if cand in tbls:
                    arg_alias = alias(tbls[cand], f"{obj_name}_{key}")
                    src = src.join(arg_alias, base_alias.c.arg1 == arg_alias.c.arg1)
                    conditions.append(arg_alias.c.arg2 == val)
                    break

        stmt = select(base_alias.c.arg1).select_from(src)
        for cond in conditions:
            stmt = stmt.where(cond)

        rows = conn.execute(stmt).fetchall()
        objs = [{"__id": row[0]} for row in rows]
        if returns_list(info.return_type):
            return objs
        return objs[0] if objs else None

    return resolver


def make_field_resolver(parent_type: str, tables: Dict[str, Table]):
    lower = parent_type.lower()

    def resolver(parent, info, **_):
        if parent is None:
            return None

        conn = info.context["conn"]
        tbls = info.context["tables"]
        field = info.field_name
        pid = parent["__id"]
        ret_typ = info.return_type

        tbl_name = next(
            (n for n in (f"{lower}_{field}_ext", f"{field}_ext") if n in tbls),
            None,
        )
        if tbl_name is None:
            return [] if returns_list(ret_typ) else None

        tbl = tbls[tbl_name]
        if is_scalar(ret_typ):
            rows = conn.execute(
                select(tbl.c.arg2).where(tbl.c.arg1 == pid)
            ).fetchall()
            vals = [r[0] for r in rows if r[0] is not None]
            if returns_list(ret_typ):
                return vals
            return vals[0] if vals else ""

        rows = conn.execute(
            select(tbl.c.arg2).where(tbl.c.arg1 == pid)
        ).fetchall()
        kids = [{"__id": r[0]} for r in rows if r[0] is not None]
        if returns_list(ret_typ):
            return kids
        return kids[0] if kids else None

    return resolver


def run_sqlite_case(
    engine: Engine,
    tables: Dict[str, Table],
    schema_path: Path,
    query_path: Path,
    runs: int,
) -> Tuple[int, float, float, float, dict]:
    """
    Execute the GraphQL query via Ariadne + SQLite. Return:
    (row_count, min_time, avg_time, max_time, last_data)
    """
    schema_sdl = gql(schema_path.read_text())
    gql_schema = build_ast_schema(parse(schema_sdl))

    query_type = QueryType()
    root_type = gql_schema.get_type("Query")
    for field_name, field_def in root_type.fields.items():
        base = unwrap(field_def.type).name
        query_type.set_field(field_name, make_root_resolver(base, tables))

    object_types: List[ObjectType] = []
    for type_name, gql_type in gql_schema.type_map.items():
        if type_name in ("Query", "Mutation") or type_name.startswith("__"):
            continue
        if not hasattr(gql_type, "fields"):
            continue
        obj = ObjectType(type_name)
        fallback = make_field_resolver(type_name, tables)
        for fname in gql_type.fields:
            obj.set_field(fname, fallback)
        object_types.append(obj)

    schema_exec = make_executable_schema(
        schema_sdl, query_type, *object_types
    )
    query_str = query_path.read_text()

    def count_scalars(data) -> int:
        if data is None:
            return 0
        if isinstance(data, (str, int, float, bool)):
            return 1
        if isinstance(data, list):
            return sum(count_scalars(x) for x in data)
        if isinstance(data, dict):
            return sum(count_scalars(v) for v in data.values())
        return 0

    times: List[float] = []
    last_data = None
    with engine.connect() as conn:
        ctx = {"conn": conn, "tables": tables}
        for _ in range(runs):
            t0 = time.perf_counter()
            result = graphql_sync(
                schema_exec, query_str, context_value=ctx
            )
            t1 = time.perf_counter()
            if result.errors:
                raise RuntimeError(result.errors)
            times.append(t1 - t0)
            last_data = result.data

    row_count = count_scalars(last_data)
    return row_count, min(times), statistics.mean(times), max(times), last_data


def run_xsb_variant(
    xsb_path: str,
    facts_path: Path,
    schema_path: Path,
    query_path: Path,
    runs: int,
    apply_demand: bool,
) -> Tuple[int, float, float, float, List[str]]:
    """
    Generate XSB code, write a Prolog driver that consults facts and the
    generated rules, runs `ans(...)` once, and captures timing. Returns:
    (row_count, min_time, avg_time, max_time, output_lines)
    """
    code = translate_graphql_to_xsb(
        str(schema_path), str(query_path), apply_demand
    )

    # Compute ans arity
    import re
    m = re.search(r"^ans\(([^)]*)\)", code, re.MULTILINE)
    if m:
        args = m.group(1).strip()
        arity = 0 if not args else args.count(',') + 1
    else:
        arity = 0

    driver_name = facts_path.parent / f"run_{'demand' if apply_demand else 'nodemand'}.P"
    ans_unders = ','.join('_' for _ in range(arity))
    ans_directive = f"\n:- ans({ans_unders}), halt."

    with open(driver_name, 'w') as drv:
        drv.write(f":- ['{facts_path.name}'].")
        drv.write(code)
        drv.write("")
        drv.write(ans_directive)

    times: List[float] = []
    output_lines: List[str] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        proc = subprocess.run(
            [xsb_path, '-e', f"['{driver_name.name}']."],
            cwd=facts_path.parent,
            capture_output=True,
            text=True,
        )
        t1 = time.perf_counter()
        if proc.returncode != 0:
            raise RuntimeError(f"XSB error: {proc.stderr}")
        times.append(t1 - t0)
        for ln in proc.stdout.splitlines():
            if ln and ln.strip() != 'DONE':
                output_lines.append(ln.strip())

    driver_name.unlink()
    row_count = len(output_lines)
    return row_count, min(times), statistics.mean(times), max(times), output_lines


def bench_folder(
    folder: Path,
    runs: int,
    xsb_path: str,
) -> None:
    print(f"=== {folder.name} ===")
    engine = create_engine("sqlite:///:memory:")
    facts_path = folder / "facts.P"
    tables = load_facts(engine, facts_path)

    # SQLite execution
    _, s_min, s_avg, s_max, _ = run_sqlite_case(
        engine,
        tables,
        folder / "schema.graphql",
        folder / "query.graphql",
        runs,
    )
    print(
        f"SQLite timing: min/avg/max = {s_min:.6f}/{s_avg:.6f}/{s_max:.6f} s"
    )

    # XSB no-demand timing
    _, x0_min, x0_avg, x0_max, _ = run_xsb_variant(
        xsb_path,
        facts_path,
        folder / "schema.graphql",
        folder / "query.graphql",
        runs,
        False,
    )
    print(
        f"XSB no-demand timing: min/avg/max = {x0_min:.6f}/{x0_avg:.6f}/{x0_max:.6f} s"
    )

    # XSB with demand timing
    _, x1_min, x1_avg, x1_max, _ = run_xsb_variant(
        xsb_path,
        facts_path,
        folder / "schema.graphql",
        folder / "query.graphql",
        runs,
        True,
    )
    print(
        f"XSB demand timing:    min/avg/max = {x1_min:.6f}/{x1_avg:.6f}/{x1_max:.6f} s"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark GraphQL ↔ SQLite vs. XSB"
    )
    parser.add_argument("tests_root", type=Path, help="Directory containing test case folders")
    parser.add_argument("--runs", type=int, default=5, help="Number of iterations per backend")
    parser.add_argument("--xsb-path", type=str, required=True, help="Path to XSB executable")
    args = parser.parse_args()

    for sub in sorted(args.tests_root.iterdir()):
        if not sub.is_dir():
            continue
        names = {p.name for p in sub.iterdir()}
        if {"facts.P", "schema.graphql", "query.graphql"}.issubset(names):
            bench_folder(sub, args.runs, args.xsb_path)

    clean(supress=True)


if __name__ == "__main__":
    main()
