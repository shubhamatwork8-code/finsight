from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine():
    url = get_settings().database_url
    connect_args = {}
    kwargs = {"future": True}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool
    return create_engine(url, connect_args=connect_args, **kwargs)


engine = _engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_ledger_currency_column()


def _ensure_column(table: str, column: str, ddl: str) -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if not inspector.has_table(table):
        return
    names = {item["name"] for item in inspector.get_columns(table)}
    if column in names:
        return
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def _ensure_ledger_currency_column() -> None:
    _ensure_column("risk_settings", "ledger_currency", "ledger_currency VARCHAR(3) DEFAULT 'USD'")
    _ensure_column("risk_settings", "user_id", "user_id VARCHAR(32)")
    _ensure_column("users", "password_hash", "password_hash VARCHAR(255)")
    _ensure_column("audit_logs", "user_id", "user_id VARCHAR(32)")
    _ensure_column("transactions", "rule_score", "rule_score INTEGER DEFAULT 0")
    _ensure_column("transactions", "ml_score", "ml_score INTEGER DEFAULT 0")
    _ensure_column("ledger_entries", "generation", "generation INTEGER DEFAULT 0")
    _ensure_column("ledger_entries", "entry_kind", "entry_kind VARCHAR(16) DEFAULT 'ORIGINAL'")
