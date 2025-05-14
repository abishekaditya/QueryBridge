"""
sqlite_setup.py
===============

Utility functions for building a SQLite database from a GraphQL schema and an
XSB facts file.  The implementation is intentionally *minimal* – it supports
exactly the constructs used by `tests/basic`, but is organised so you can
extend it for richer schemas.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Dict, List

_CREATE_TABLE_PATTERN = re.compile(r"type\s+(\w+)\s*{", re.IGNORECASE)
_FIELD_PATTERN = re.compile(r"\s*(\w+)\s*:\s*(\w+)!?", re.IGNORECASE)


def _parse_schema(schema_path: Path) -> Dict[str, List[str]]:
    """Very small SDL parser: returns {table_name: [field1, ...]}"""
    tables: Dict[str, List[str]] = {}
    current = None
    for line in schema_path.read_text().splitlines():
        m_table = _CREATE_TABLE_PATTERN.match(line)
        if m_table:
            current = m_table.group(1)
            tables[current] = []
            continue
        if current:
            if line.strip() == "}":
                current = None
                continue
            m_field = _FIELD_PATTERN.match(line)
            if m_field:
                tables[current].append(m_field.group(1))
    return tables


_FACT_PATTERN = re.compile(r"(\w+)\(([^)]*)\)\.")


def _parse_facts(facts_path: Path) -> Dict[str, List[List[str]]]:
    """Return mapping {predicate: [[arg1, arg2], ...]}"""
    data: Dict[str, List[List[str]]] = {}
    for line in facts_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('%'):
            continue
        m = _FACT_PATTERN.match(line)
        if not m:
            continue
        pred = m.group(1)
        args = [a.strip("' \t\"") for a in m.group(2).split(',')]
        data.setdefault(pred, []).append(args)
    return data


def generate_sqlite_db(schema_path: Path, facts_path: Path, db_path: Path) -> None:
    """Create or overwrite *db_path* with data derived from GraphQL schema + XSB facts."""
    tables = _parse_schema(schema_path)
    facts = _parse_facts(facts_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create tables
    for table, cols in tables.items():
        col_defs = ', '.join(f'{c} TEXT' for c in cols or ['value'])
        cur.execute(f'DROP TABLE IF EXISTS {table}')
        cur.execute(f'CREATE TABLE {table} ({col_defs})')

    # Insert data
    for pred, rows in facts.items():
        if pred not in tables:
            # Skip predicates that aren't in the schema
            continue
        placeholders = ', '.join('?' for _ in tables[pred])
        cur.executemany(
            f'INSERT INTO {pred} VALUES ({placeholders})',
            rows,
        )

    conn.commit()
    conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Build SQLite DB from schema + facts')
    parser.add_argument('--schema', type=Path, required=True)
    parser.add_argument('--facts', type=Path, required=True)
    parser.add_argument('--db', type=Path, required=True)
    args = parser.parse_args()

    generate_sqlite_db(args.schema, args.facts, args.db)
