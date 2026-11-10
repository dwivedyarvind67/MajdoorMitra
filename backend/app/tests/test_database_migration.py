"""Backwards-compatible database upgrades."""

from sqlalchemy import create_engine, inspect, text

from app.database.connection import _add_confirmed_at_if_missing


def test_confirmed_at_upgrade_adds_column_once():
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE voice_statements (id VARCHAR(36) PRIMARY KEY)"))
            _add_confirmed_at_if_missing(connection)
            _add_confirmed_at_if_missing(connection)

            columns = {column["name"] for column in inspect(connection).get_columns("voice_statements")}
            assert "confirmed_at" in columns
            assert columns == {"id", "confirmed_at"}
    finally:
        engine.dispose()
