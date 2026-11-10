"""Backwards-compatible database upgrades."""

from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text, select

from app.database.connection import Base, _add_confirmed_at_if_missing, upgrade_schema
from app.models.models import WorkEntry, Worker


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


def test_additive_schema_upgrade_preserves_existing_worker_and_work_rows():
    engine = create_engine("sqlite:///:memory:")
    try:
        legacy_tables = [
            table for table in Base.metadata.sorted_tables
            if table.name not in {"audit_events", "payment_allocations", "work_entries"}
        ]
        with engine.begin() as connection:
            Base.metadata.create_all(connection, tables=legacy_tables)
            connection.execute(text("""
                CREATE TABLE work_entries (
                    id VARCHAR(36) PRIMARY KEY,
                    worker_id VARCHAR(36) NOT NULL REFERENCES workers(id),
                    employer_id VARCHAR(36), work_date DATETIME NOT NULL,
                    days_worked NUMERIC(15, 2) NOT NULL, hours_worked NUMERIC(15, 2),
                    daily_wage NUMERIC(15, 2) NOT NULL, total_earned NUMERIC(15, 2) NOT NULL,
                    description TEXT, source_statement_id VARCHAR(36), created_at DATETIME NOT NULL
                )
            """))
            connection.execute(
                Worker.__table__.insert().values(
                    id="legacy-worker",
                    name="Legacy Worker",
                    phone="9876500000",
                    preferred_language="hi",
                    pin_hash="test-hash",
                    created_at=datetime.now(timezone.utc),
                )
            )
            connection.execute(
                text("""INSERT INTO work_entries
                    (id, worker_id, work_date, days_worked, daily_wage, total_earned, created_at)
                    VALUES (:id, :worker, :date, :days, :wage, :earned, :created)"""),
                {
                    "id": "legacy-work",
                    "worker": "legacy-worker",
                    "date": datetime(2026, 11, 10, tzinfo=timezone.utc),
                    "days": 1,
                    "wage": 700,
                    "earned": 700,
                    "created": datetime.now(timezone.utc),
                },
            )

            assert "audit_events" not in inspect(connection).get_table_names()
            assert "wage_basis" not in {c["name"] for c in inspect(connection).get_columns("work_entries")}
            upgrade_schema(connection)

            assert connection.execute(select(Worker.id)).scalars().all() == ["legacy-worker"]
            assert connection.execute(select(WorkEntry.id)).scalars().all() == ["legacy-work"]
            assert "audit_events" in inspect(connection).get_table_names()
            assert "payment_allocations" in inspect(connection).get_table_names()
            columns = {c["name"] for c in inspect(connection).get_columns("work_entries")}
            assert {"wage_basis", "hourly_rate", "overtime_hours", "overtime_multiplier"} <= columns
    finally:
        engine.dispose()
