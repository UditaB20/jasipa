"""Lightweight additive schema migration.

JASIPA has no Alembic history, so existing SQLite/PostgreSQL installs are upgraded by adding any
column that the ORM models declare but the live table lacks. New columns are always nullable,
so this never rewrites or drops existing data.
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database.session import Base


def run_additive_migrations(engine: Engine) -> list[str]:
    # Import models so every table is registered on Base.metadata before create_all.
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    added = []
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            column_type = column.type.compile(dialect=engine.dialect)
            with engine.begin() as connection:
                connection.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {column.name} {column_type}'))
            added.append(f"{table.name}.{column.name}")
    return added
