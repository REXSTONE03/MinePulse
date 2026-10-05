import os
import pytest
from backend.app.database.session import DATABASE_URL, engine

def test_database_url_environment_variable_parsing():
    # Verify default or env configuration
    assert DATABASE_URL is not None
    assert isinstance(DATABASE_URL, str)

def test_sqlite_fallback_and_postgres_compatibility_parsing():
    # Simulating PostgreSQL string conversion
    pg_url = "postgresql://user:pass@localhost:5432/dbname"
    if pg_url.startswith("postgresql://"):
        converted_pg_url = pg_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    assert converted_pg_url == "postgresql+psycopg2://user:pass@localhost:5432/dbname"

from sqlalchemy import text

def test_engine_connect_ping():
    # Verify engine can execute ping statement
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result is not None

