#!/usr/bin/env python3
"""benchmark.py – in‑process GraphQL ⇄ SQLite micro‑benchmark
============================================================

Executes each `schema.graphql` + `query.graphql` pair in the test folders
against the `*_ext` facts (loaded into an **in‑memory SQLite** database)
via **Ariadne** + **SQLAlchemy**, then prints the count of returned
leaf scalars and min/avg/max execution times over *N* iterations.

> **Fix 2025‑05‑14:** Some scalar fields may be non‑nullable in the
> schema but missing in the facts. The scalar resolver now treats
> absent or NULL values as empty strings (`""`), avoiding GraphQL
> errors for non‑nullable fields.

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
    """Parse facts of varying arity, create tables, and insert rows."""
    metadata = MetaData()
    # parse and accumulate all facts
    fact_lines = [l.strip() for l in facts_file.read_text().splitlines() if l.strip() and not l.strip().startswith('%')]
    parsed: List[Tuple[str, List[str]]] = []
    fact_re = re.compile(r'^(\w+)\((.*)\)\.$')
    for line in fact_lines:
        m = fact_re.match(line)
        if not m:
            continue
        pred, blob = m.groups()
        parts = [p.strip().strip('"') for p in blob.split(',')]
        parsed.append((pred, parts))
    # determine arity per predicate
    arity: Dict[str, int] = {}
    for pred, parts in parsed:
        arity[pred] = max(arity.get(pred, 0), len(parts))
    # create tables
    tables: Dict[str, Table] = {}
    for pred, n in arity.items():
        cols = [Column(f'arg{i+1}', Text) for i in range(n)]
        tbl = Table(pred, metadata, *cols)
        tbl.create(bind=engine)
        tables[pred] = tbl
    # insert rows with padding
    with engine.begin() as conn:
        for pred, parts in parsed:
            tbl = tables[pred]
            n = len(tbl.columns)
            padded = parts + [None] * (n - len(parts))
            ins = {f'arg{i+1}': padded[i] for i in range(n)}
            conn.execute(tbl.insert().values(ins))
    return tables

###############################################################################
# 2.  GraphQL type helpers                                                     #
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
    base_tbl = f"{obj_name.lower()}_ext"
    def resolver(_, info, **args):
        conn = info.context['conn']
        tbls = info.context['tables']
        if base_tbl not in tbls:
            return [] if returns_list(info.return_type) else None
        tbl = alias(tbls[base_tbl], obj_name)
        frm = tbl
        conds: List = []
        for k, v in args.items():
            for cand in (f"{obj_name.lower()}_{k}_ext", f"{k}_ext"):
                if cand in tbls:
                    at = alias(tbls[cand], f"{obj_name}_{k}")
                    frm = frm.join(at, tbl.c.arg1 == at.c.arg1)
                    conds.append(at.c.arg2 == v)
                    break
        stmt = select(tbl.c.arg1).select_from(frm)
        for c in conds:
            stmt = stmt.where(c)
        rows = conn.execute(stmt).fetchall()
        objs = [{"__id": r[0]} for r in rows]
        return objs if returns_list(info.return_type) else (objs[0] if objs else None)
    return resolver


def make_field_resolver(parent: str, tables: Dict[str, Table]):
    lower = parent.lower()
    def resolver(obj, info, **_):
        if obj is None:
            return None
        conn = info.context['conn']
        tbls = info.context['tables']
        fld = info.field_name
        pid = obj['__id']
        rtyp = info.return_type
        tbl_name = next((n for n in (f"{lower}_{fld}_ext", f"{fld}_ext") if n in tbls), None)
        if not tbl_name:
            return [] if returns_list(rtyp) else None
        tbl = tbls[tbl_name]
        # scalar field: gather all non-null, default to ""
        if is_scalar(rtyp):
            rows = conn.execute(select(tbl.c.arg2).where(tbl.c.arg1 == pid)).fetchall()
            vals = [r[0] for r in rows if r[0] is not None]
            if returns_list(rtyp):
                return vals
            return vals[0] if vals else ""
        # relational field
        rows = conn.execute(select(tbl.c.arg2).where(tbl.c.arg1 == pid)).fetchall()
        kids = [{"__id": r[0]} for r in rows if r[0] is not None]
        if returns_list(rtyp):
            return kids
        return kids[0] if kids else None
    return resolver

###############################################################################
# 4.  Execute & benchmark                                                     #
###############################################################################

def run_case(engine: Engine, tables: Dict[str, Table], schema_p: Path, query_p: Path, its: int) -> Tuple[int, float, float, float]:
    schema_doc = gql(schema_p.read_text())
    gql_sch = build_ast_schema(parse(schema_doc))
    qtype = QueryType()
    root = gql_sch.get_type('Query')
    if not root:
        raise ValueError('Schema must define Query')
    for name, fld in root.fields.items():
        qtype.set_field(name, make_root_resolver(unwrap(fld.type).name, tables))
    obj_types: List[ObjectType] = []
    for tname, typ in gql_sch.type_map.items():
        if tname in ('Query','Mutation') or tname.startswith('__'):
            continue
        if not hasattr(typ, 'fields'):
            continue
        ot = ObjectType(tname)
        res = make_field_resolver(tname, tables)
        for f in typ.fields:
            ot.set_field(f, res)
        obj_types.append(ot)
    exe = make_executable_schema(schema_doc, qtype, *obj_types)
    qry = query_p.read_text()
    times: List[float] = []
    maxr = 0
    def cnt(d):
        if d is None: return 0
        if isinstance(d,(str,int,float,bool)): return 1
        if isinstance(d,list): return sum(cnt(x) for x in d)
        if isinstance(d,dict): return sum(cnt(v) for v in d.values())
        return 0
    with engine.connect() as conn:
        ctx = {'conn':conn,'tables':tables}
        for _ in range(its):
            t0 = time.perf_counter()
            res = graphql_sync(exe, qry, context_value=ctx)
            t1 = time.perf_counter()
            if res.errors:
                raise RuntimeError(res.errors)
            times.append(t1-t0)
            maxr = max(maxr, cnt(res.data))
    return maxr, min(times), statistics.mean(times), max(times)

###############################################################################
# 5.  CLI                                                                     #
###############################################################################

def bench_folder(f: Path, runs: int):
    print(f"\n=== {f.name} ===")
    eng = create_engine('sqlite:///:memory:')
    tbls = load_facts(eng, f/'facts.P')
    rows, t_min, t_avg, t_max = run_case(eng, tbls, f/'schema.graphql', f/'query.graphql', runs)
    print(f"rows: {rows} | runs: {runs} | min/avg/max: {t_min:.6f} / {t_avg:.6f} / {t_max:.6f} s")


def main():
    p = argparse.ArgumentParser('Benchmark GraphQL ↔ SQLite')
    p.add_argument('tests_root',type=Path)
    p.add_argument('--runs',type=int,default=5)
    ns = p.parse_args()
    if not ns.tests_root.is_dir():
        raise SystemExit('tests_root must be a directory')
    for sub in sorted(ns.tests_root.iterdir()):
        if sub.is_dir() and {'facts.P','schema.graphql','query.graphql'}.issubset({x.name for x in sub.iterdir()}):
            bench_folder(sub, ns.runs)

if __name__=='__main__':
    main()
