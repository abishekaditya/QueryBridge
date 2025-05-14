#!/usr/bin/env python3
"""benchmark.py – QueryBridge benchmark (XSB-centric, no SQL fallbacks)

This lightweight harness measures two execution strategies for a GraphQL
query stored in a given test directory:

1. XSB **without** demand transformation
2. XSB **with** demand transformation

If *querybridge.translator* also exposes `translate_graphql_to_sql()`, we add
optional measurements for:

3. Raw SQL on SQLite
4. SQLAlchemy Core on SQLite

But **no additional SQL synthesiser** is attempted – if the SQL translator is
missing, we simply skip the SQL/ORM paths. This avoids extra dependencies and
eliminates compatibility issues like the `visit_with_type_info` import error.

Usage::
    python benchmark.py --test-dir tests/basic
"""
from __future__ import annotations

import argparse
import importlib
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from textwrap import dedent
from typing import Callable, Optional, Tuple

# ───────────────────────────── QueryBridge imports ───────────────────────────
try:
    qb = importlib.import_module("querybridge.translator")
    translate_graphql_to_xsb: Callable = qb.translate_graphql_to_xsb  # type: ignore[attr-defined]
    translate_graphql_to_sql: Optional[Callable] = getattr(qb, "translate_graphql_to_sql", None)
except ImportError:
    sys.stderr.write("✖️  Could not import QueryBridge – is it installed / on PYTHONPATH?\n")
    raise

# ─────────────────────────── local helper (SQLite build) ─────────────────────
from sqlite_setup import generate_sqlite_db  # type: ignore

# ═══════════════════════════ helper utilities ═══════════════════════════════

def _decode(buf: str | bytes | None) -> str:
    if buf is None:
        return ""
    if isinstance(buf, (bytes, bytearray)):
        return buf.decode("utf-8", errors="replace")
    return buf


def _run_xsb(pfile: Path, cwd: Path, timeout: int = 60) -> Tuple[list[str], float]:
    """Run an XSB program and return (answers, seconds)."""
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            ["xsb", "-e", f"['{pfile.name}']."],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        print(f"⏰  XSB timed out after {timeout}s while running {pfile.name}")
        print("— STDOUT so far —\n" + _decode(exc.stdout))
        print("— STDERR so far —\n" + _decode(exc.stderr))
        raise

    dur = time.perf_counter() - start
    if proc.returncode != 0:
        print(f"💥  XSB exited with status {proc.returncode} while running {pfile.name}")
        print("— STDOUT —\n" + proc.stdout)
        print("— STDERR —\n" + proc.stderr)

    answers = [ln.split("Result: ", 1)[1] for ln in proc.stdout.splitlines() if ln.startswith("Result: ")]
    return answers, dur


def _run_sql(conn: sqlite3.Connection, sql: str) -> Tuple[list[tuple], float]:
    cur = conn.cursor()
    start = time.perf_counter()
    cur.execute(sql)
    rows = cur.fetchall()
    return rows, time.perf_counter() - start


def _run_sqlalchemy(db: Path, table: str, column: str) -> Tuple[list[str], float]:
    from sqlalchemy import create_engine, MetaData, select
    from sqlalchemy.orm import Session

    engine = create_engine(f"sqlite:///{db}")
    md = MetaData()
    md.reflect(bind=engine)
    col = md.tables[table].c[column]

    session = Session(engine)
    start = time.perf_counter()
    rows = session.execute(select(col)).scalars().all()
    dur = time.perf_counter() - start
    session.close()
    return rows, dur

# ═══════════════════════════ benchmark logic ═══════════════════════════════

def benchmark(test_dir: Path) -> None:
    schema = test_dir / "schema.graphql"
    query = test_dir / "query.graphql"
    facts = next((test_dir / fn for fn in ("facts.P", "facts.xsb") if (test_dir / fn).exists()), None)

    if not (schema.exists() and query.exists() and facts):
        raise FileNotFoundError("schema.graphql, query.graphql, and facts.(P|xsb) required in test dir")

    print("→ Translating GraphQL to XSB …")
    xsb_no = translate_graphql_to_xsb(schema, query, apply_demand=False)
    xsb_yes = translate_graphql_to_xsb(schema, query, apply_demand=True)

    facts_p = test_dir / "facts.P"
    if not facts_p.exists():
        facts_p.write_text(facts.read_text())

    def _wrap(code: str, name: str) -> Path:
        p = test_dir / name
        p.write_text(
            dedent(
                f""":- ['facts.P'].

{code}

run_query :- ans(Tagline), write('Result: '), write(Tagline), nl, fail.
run_query :- write('Query completed.'), nl.

:- run_query.
:- halt.
"""
            )
        )
        return p

    p_no = _wrap(xsb_no, "run_no.P")
    p_yes = _wrap(xsb_yes, "run_yes.P")

    db_path = test_dir / "benchmark.db"
    if db_path.exists():
        db_path.unlink()

    sql_available = translate_graphql_to_sql is not None
    table = column = sql_stmt = ""

    if sql_available:
        print("→ Translating GraphQL to raw SQL via QueryBridge …")
        sql_stmt = translate_graphql_to_sql(schema, query)  # type: ignore[arg-type]
        toks = sql_stmt.split()
        column = toks[1] if len(toks) >= 2 else ""
        table = toks[3] if len(toks) >= 4 else ""
        if not (table and column):
            print("⚠️  Could not parse table/column from generated SQL – skipping SQL paths.")
            sql_available = False

    # Always build DB if SQL tests requested
    if sql_available:
        print("→ Building SQLite DB …")
        generate_sqlite_db(schema, facts, db_path)

    # ─── run XSB variants ───────────────────────────────────────────────────
    print("→ Running XSB WITHOUT demand …")
    res_no, t_no = _run_xsb(p_no, test_dir)

    print("→ Running XSB WITH demand …")
    res_yes, t_yes = _run_xsb(p_yes, test_dir)

    # ─── optional SQL / ORM paths ──────────────────────────────────────────
    res_sql: list[tuple] = []
    t_sql = 0.0
    res_orm: list[str] = []
    t_orm = 0.0

    if sql_available:
        print("→ Running raw SQL …")
        with sqlite3.connect(db_path) as conn:
            res_sql, t_sql = _run_sql(conn, sql_stmt)

        print("→ Running SQLAlchemy …")
        res_orm, t_orm = _run_sqlalchemy(db_path, table, column)

    # ─── validate results ─────────────────────────────────────────────────
    expected = set(res_no)
    mismatches = []
    if set(res_yes) != expected:
        mismatches.append("XSB-with-demand")
    if sql_available and {r[0] for r in res_sql} != expected:
        mismatches.append("raw-SQL")
    if sql_available and set(res_orm) != expected:
        mismatches.append("ORM")
    if mismatches:
        raise AssertionError("Mismatch between strategies: " + ", ".join(mismatches))

    # ─── report ────────────────────────────────────────────────────────────
    print("\n=== Benchmark complete ===")
    print(f"XSB   (no demand)   : {t_no * 1_000:8.2f} ms | rows = {len(res_no)}")
    print(f"XSB   (with demand) : {t_yes * 1_000:8.2f} ms | rows = {len(res_yes)}")
    if sql_available:
        print(f"SQLite (raw SQL)    : {t_sql * 1_000:8.2f} ms | rows = {len(res_sql)}")
        print(f"SQLAlchemy          : {t_orm * 1_000:8.2f} ms | rows = {len(res_orm)}")
    else:
        print("Raw SQL / ORM skipped – translate_graphql_to_sql() unavailable.")

# ═══════════════════════════ CLI entry point ═══════════════════════════════

def cli() -> None:
    parser = argparse.ArgumentParser(description="Benchmark QueryBridge backends (XSB-focused)")
    parser.add_argument("--test-dir", type=Path, default=Path("tests") / "basic", help="Directory with schema.graphql, query.graphql, facts.*")
    args = parser.parse_args()
    benchmark(args.test_dir)


if __name__ == "__main__":
    cli()
