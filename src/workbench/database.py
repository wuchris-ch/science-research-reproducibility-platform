"""Transactional metadata. SQLite is the zero-service local profile; PostgreSQL is supported."""

import time
import uuid
from contextlib import contextmanager

from sqlalchemy import (
    JSON,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    event,
    insert,
    select,
    text,
)

metadata = MetaData()
workspaces = Table(
    "workspaces",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("created", Float, nullable=False),
)
members = Table(
    "members",
    metadata,
    Column("workspace_id", ForeignKey("workspaces.id"), primary_key=True),
    Column("subject", String, primary_key=True),
    Column("role", String, nullable=False),
)
plans = Table(
    "plans",
    metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", ForeignKey("workspaces.id"), nullable=False, index=True),
    Column("revision", Integer, nullable=False),
    Column("state", String, nullable=False),
    Column("body", JSON, nullable=False),
    Column("created", Float, nullable=False),
)
revisions = Table(
    "plan_revisions",
    metadata,
    Column("plan_id", ForeignKey("plans.id"), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("body", JSON, nullable=False),
    Column("actor", String, nullable=False),
    Column("created", Float, nullable=False),
)
runs = Table(
    "runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", ForeignKey("workspaces.id"), nullable=False, index=True),
    Column("plan_id", ForeignKey("plans.id"), nullable=False),
    Column("key", String, nullable=False),
    Column("request_hash", String, nullable=False),
    Column("state", String, nullable=False, index=True),
    Column("epoch", Integer, nullable=False, default=0),
    Column("owner", String),
    Column("lease_until", Float, nullable=False, default=0),
    Column("cancel_requested", Integer, nullable=False, default=0),
    Column("body", JSON, nullable=False),
    Column("created", Float, nullable=False),
    Column("updated", Float, nullable=False),
    UniqueConstraint("workspace_id", "key"),
)
attempts = Table(
    "attempts",
    metadata,
    Column("run_id", ForeignKey("runs.id"), primary_key=True),
    Column("epoch", Integer, primary_key=True),
    Column("body", JSON, nullable=False),
)
events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workspace_id", ForeignKey("workspaces.id"), nullable=False, index=True),
    Column("run_id", ForeignKey("runs.id")),
    Column("kind", String, nullable=False),
    Column("actor", String, nullable=False),
    Column("body", JSON, nullable=False),
    Column("created", Float, nullable=False),
)
reviews = Table(
    "reviews",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", ForeignKey("runs.id"), nullable=False),
    Column("actor", String, nullable=False),
    Column("body", JSON, nullable=False),
    Column("created", Float, nullable=False),
)
attachments = Table(
    "attachments",
    metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", ForeignKey("workspaces.id"), nullable=False),
    Column("body", JSON, nullable=False),
    Column("created", Float, nullable=False),
)
model_calls = Table(
    "model_calls",
    metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", ForeignKey("workspaces.id"), nullable=False),
    Column("reserved", Float, nullable=False),
    Column("actual", Float),
    Column("body", JSON, nullable=False),
    Column("created", Float, nullable=False),
)


def uid():
    return uuid.uuid4().hex


class Database:
    def __init__(self, url: str):
        self.engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite:") else {},
        )
        if url.startswith("sqlite:"):

            @event.listens_for(self.engine, "connect")
            def configure(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA busy_timeout=30000")

    def migrate(self):
        # The first additive schema migration; version checked before serving.
        with self.transaction() as c:
            if self.engine.dialect.name == "postgresql":
                c.execute(text("SELECT pg_advisory_xact_lock(83717001)"))
            c.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"))
            version = c.execute(text("SELECT version FROM schema_version")).scalar()
            if version not in (None, 1):
                raise RuntimeError("Unsupported database version; use a matching application version")
            metadata.create_all(c)
            if version is None:
                c.execute(text("INSERT INTO schema_version (version) VALUES (1)"))

    @contextmanager
    def transaction(self):
        with self.engine.connect() as connection:
            if self.engine.dialect.name == "sqlite":
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                connection.begin()
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    @staticmethod
    def row(c, table, identity):
        return c.execute(select(table).where(table.c.id == identity)).mappings().first()

    @staticmethod
    def emit(c, workspace_id, kind, actor, body=None, run_id=None):
        c.execute(
            insert(events).values(
                workspace_id=workspace_id,
                run_id=run_id,
                kind=kind,
                actor=actor,
                body=body or {},
                created=time.time(),
            )
        )
