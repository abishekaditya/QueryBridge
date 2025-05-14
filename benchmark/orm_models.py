"""
orm_models.py
==============

Light‑weight helper that builds SQLAlchemy runtime models *at execution time*
by reflecting the database – this means you don't need to regenerate models
every time the schema changes.

The function `build_session_and_query()` returns a `(Session, Query)` tuple
so the caller can time the ORM execution separately.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.automap import automap_base


def build_session_and_query(db_path: Path):
    """Return (Session, Query) configured for *db_path*.

    The Query selects everything the GraphQL query is expected to return.
    For the basic test‑case this is a single `tagline` column.  If you need
    to expose more complex selections just adjust the query construction
    below.
    """
    engine = create_engine(f'sqlite:///{db_path}')
    Base = automap_base()
    Base.prepare(autoload_with=engine)

    # We expect a single table – if there are multiple just pick the first
    # because the basic test only queries one entity.
    mapped_cls = next(iter(Base.classes))

    session = Session(engine)

    # Construct a SELECT; SQLAlchemy 2.x uses the new select() construct.
    query = session.execute(select(mapped_cls)).scalars()

    # Caller is responsible for closing the session.
    return session, query
