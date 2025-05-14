#!/usr/bin/env python3
"""benchmark.py – in-process GraphQL ⇄ SQLite micro-benchmark
============================================================

Runs every `schema.graphql` + `query.graphql` pair in the test folders
against the `*_ext` facts (loaded into an **in-memory SQLite** database)
via **Ariadne** + **SQLAlchemy**.  Each folder prints the number of leaf
scalars returned and min/avg/max execution time over *N* iterations.

> **Fix 2025-05-14:** SQLAlchemy 2.x no longer lets you call `.where()`
> on the `Join` object that `.join()` returns.  The resolver now builds a
> list of **conditions** and applies them to the final `select(...)`, so
> it works on both 1.4 and 2.x.

Usage
-----
```bash
pip install ariadne graphql-core sqlalchemy
python benchmark.py tests --runs 10
```
"""
from __future__ import annotations

import argparse
import re
import statistics
import time
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

###############################################################################
# 1.  Load facts.P into SQLite                                                #
###############################################################################

def load_facts(engine: Engine, facts_file: Path) -> Dict[str, Table]:
    metadata = MetaData()
    tables: Dict[str, Table] = {}
    fact_re = re.compile(r"^(\w+)\s*\((.*)\)\s*\.$")
    with engine.begin() as conn:
        for raw in facts_file.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("%"):
                continue
            m = fact_re.match(line)
            if not m:
                continue
            pred, arg_blob = m.groups()
            parts = [p.strip().strip('"') for p in re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", arg_blob)]
            tbl = tables.get(pred)
            if tbl is None:
                cols = [Column(f"arg{i+1}", Text) for i in range(len(parts))]
                tbl = Table(pred, metadata, *cols)
                tbl.create(bind=engine)
                tables[pred] = tbl
            conn.execute(tbl.insert().values({f"arg{i+1}": v for i, v in enumerate(parts)}))
    return tables

###############################################################################
# 2.  GraphQL helpers                                                         #
###############################################################################

def unwrap(typ):
    while isinstance(typ, (GraphQLNonNull, GraphQLList)):
        typ = typ.of_type
    return typ


def is_scalar(typ):
    return isinstance(unwrap(typ), GraphQLScalarType)


def returns_list(typ):
    return isinstance(typ, GraphQLList) or (
        isinstance(typ, GraphQLNonNull) and isinstance(typ.of_type, GraphQLList)
    )

###############################################################################
# 3.  Resolver factories                                                      #
###############################################################################

def make_root_resolver(obj_name: str, tables: Dict[str, Table]):
    base_tbl_name = f"{obj_name.lower()}_ext"

    def resolver(_, info, **args):
        conn = info.context["conn"]
        tbls = info.context["tables"]
        if base_tbl_name not in tbls:
            return [] if returns_list(info.return_type) else None

        base_tbl = alias(tbls[base_tbl_name], obj_name)
        current_from = base_tbl
        conditions = []

        for arg_key, lit in args.items():
            for cand in (f"{obj_name.lower()}_{arg_key}_ext", f"{arg_key}_ext"):
                if cand in tbls:
                    arg_tbl = alias(tbls[cand], f"{obj_name}_{arg_key}")
                    current_from = current_from.join(arg_tbl, base_tbl.c.arg1 == arg_tbl.c.arg1)
                    conditions.append(arg_tbl.c.arg2 == lit)
                    break
        sel = select(base_tbl.c.arg1).select_from(current_from)
        for cond in conditions:
            sel = sel.where(cond)
        rows = conn.execute(sel).fetchall()
        objs = [{"__id": r[0]} for r in rows]
        return objs if returns_list(info.return_type) else (objs[0] if objs else None)

    return resolver


def make_field_resolver(parent_type: str, tables: Dict[str, Table]):
    parent_lower = parent_type.lower()

    def resolver(parent, info, **_):
        if parent is None:
            return None
        conn = info.context["conn"]
        tbls = info.context["tables"]
        field = info.field_name
        parent_id = parent["__id"]
        return_type = info.return_type

        tbl_name = next((n for n in (f"{parent_lower}_{field}_ext", f"{field}_ext") if n in tbls), None)
        if tbl_name is None:
            return [] if returns_list(return_type) else None
        tbl = tbls[tbl_name]

        if is_scalar(return_type):
            row = conn.execute(select(tbl.c.arg2).where(tbl.c.arg1 == parent_id)).fetchone()
            return row[0] if row else None
        rows = conn.execute(select(tbl.c.arg2).where(tbl.c.arg1 == parent_id)).fetchall()
        kids = [{"__id": r[0]} for r in rows]
        return kids if returns_list(return_type) else (kids[0] if kids else None)

    return resolver

###############################################################################
# 4.  Execute & time a single test-case                                       #
###############################################################################

def run_case(engine: Engine, tables: Dict[str, Table], schema_path: Path, query_path: Path, iters: int) -> Tuple[int, float, float, float]:
    sdl = gql(schema_path.read_text())
    gql_schema = build_ast_schema(parse(sdl))

    query_type = QueryType()
    root_obj = gql_schema.get_type("Query")
    if root_obj is None:
        raise ValueError("Schema missing Query type")
    for root_name, root_field in root_obj.fields.items():
        query_type.set_field(root_name, make_root_resolver(unwrap(root_field.type).name, tables))

    obj_types: List[ObjectType] = []
    for name, gql_t in gql_schema.type_map.items():
        if name in ("Query", "Mutation") or name.startswith("__"):
            continue
        if not hasattr(gql_t, "fields"):
            continue
        obj = ObjectType(name)
        fallback = make_field_resolver(name, tables)
        for fld in gql_t.fields.keys():
            obj.set_field(fld, fallback)
        obj_types.append(obj)

    schema = make_executable_schema(sdl, query_type, *obj_types)
    query = query_path.read_text()

    times: List[float] = []
    max_rows = 0

    def count_scalars(data):
        if data is None:
            return 0
        if isinstance(data, (str, int, float, bool)):
            return 1
        if isinstance(data, list):
            return sum(count_scalars(x) for x in data)
        if isinstance(data, dict):
            return sum(count_scalars(v) for v in data.values())
        return 0

    with engine.connect() as conn:
        ctx = {"conn": conn, "tables": tables}
        for _ in range(iters):
            t0 = time.perf_counter()
            res = graphql_sync(schema, query, context_value=ctx)
            t1 = time.perf_counter()
            if res.errors:
                raise RuntimeError(res.errors)
            times.append(t1 - t0)
            max_rows = max(max_rows, count_scalars(res.data))

    return max_rows, min(times), statistics.mean(times), max(times)

###############################################################################
# 5.  CLI                                                                     #
###############################################################################

def bench_folder(folder: Path, runs: int):
    print(f"\n=== {folder.name} ===")
    engine = create_engine("sqlite:///:memory:")
    tables = load_facts(engine, folder / "facts.P")
    rows, t_min, t_avg, t_max = run_case(engine, tables, folder / "schema.graphql", folder / "query.graphql", runs)
    print(f"rows: {rows} | runs: {runs} | min/avg/max: {t_min:.6f} / {t_avg:.6f} / {t_max:.6f} s")


def main():
    ap = argparse.ArgumentParser(description="Benchmark GraphQL ↔ SQLite with Ariadne & SQLAlchemy")
    ap.add_argument("tests_root", type=Path)
    ap.add_argument("--runs", type=int, default=5)
    ns = ap.parse_args()

    if not ns.tests_root.is_dir():
        raise SystemExit("tests_root must be a directory")

    for sub in sorted(ns.tests_root.iterdir()):
        if sub.is_dir() and {"facts.P", "schema.graphql", "query.graphql"}.issubset({p.name for p in sub.iterdir()}):
            bench_folder(sub, ns.runs)


if __name__ == "__main__":
    main()
