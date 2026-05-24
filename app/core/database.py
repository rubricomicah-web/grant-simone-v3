from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings


def normalize_database_url(url: str) -> str:
    """Make Railway/Postgres URLs work with installed psycopg v3.

    Railway commonly provides DATABASE_URL as postgresql://... or postgres://...
    SQLAlchemy's default PostgreSQL driver expects psycopg2 unless we explicitly
    select psycopg v3 using postgresql+psycopg://.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url

DATABASE_URL = normalize_database_url(settings.database_url)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _column_exists(conn, table: str, column: str) -> bool:
    try:
        if DATABASE_URL.startswith("sqlite"):
            rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            return any(r[1] == column for r in rows)
        rows = conn.exec_driver_sql(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
            (table, column),
        ).fetchall()
        return bool(rows)
    except Exception:
        return True

def _add_column_if_missing(conn, table: str, column: str, ddl: str):
    if not _column_exists(conn, table, column):
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {ddl}")

def run_lightweight_migrations():
    """Small safe migrations for Railway deployments using create_all.

    SQLAlchemy create_all does not add columns to existing tables. These additions
    keep older test deployments from crashing when the hardened auth fields are introduced.
    """
    with engine.begin() as conn:
        if DATABASE_URL.startswith("sqlite"):
            _add_column_if_missing(conn, "users", "email_verified", "email_verified BOOLEAN DEFAULT 0")
            _add_column_if_missing(conn, "users", "email_verification_token_hash", "email_verification_token_hash VARCHAR(128)")
            _add_column_if_missing(conn, "users", "email_verification_sent_at", "email_verification_sent_at DATETIME")
            _add_column_if_missing(conn, "users", "password_reset_token_hash", "password_reset_token_hash VARCHAR(128)")
            _add_column_if_missing(conn, "users", "password_reset_expires_at", "password_reset_expires_at DATETIME")
            _add_column_if_missing(conn, "users", "failed_login_attempts", "failed_login_attempts INTEGER DEFAULT 0")
            _add_column_if_missing(conn, "users", "locked_until", "locked_until DATETIME")
            _add_column_if_missing(conn, "users", "last_login_at", "last_login_at DATETIME")
        else:
            _add_column_if_missing(conn, "users", "email_verified", "email_verified BOOLEAN DEFAULT false")
            _add_column_if_missing(conn, "users", "email_verification_token_hash", "email_verification_token_hash VARCHAR(128)")
            _add_column_if_missing(conn, "users", "email_verification_sent_at", "email_verification_sent_at TIMESTAMP WITH TIME ZONE")
            _add_column_if_missing(conn, "users", "password_reset_token_hash", "password_reset_token_hash VARCHAR(128)")
            _add_column_if_missing(conn, "users", "password_reset_expires_at", "password_reset_expires_at TIMESTAMP WITH TIME ZONE")
            _add_column_if_missing(conn, "users", "failed_login_attempts", "failed_login_attempts INTEGER DEFAULT 0")
            _add_column_if_missing(conn, "users", "locked_until", "locked_until TIMESTAMP WITH TIME ZONE")
            _add_column_if_missing(conn, "users", "last_login_at", "last_login_at TIMESTAMP WITH TIME ZONE")

def init_db():
    from app.models.tables import Base as ModelBase
    ModelBase.metadata.create_all(bind=engine)
    run_lightweight_migrations()
    # No seed or fallback grants. The database starts empty until real verified
    # grants are ingested from official/live sources or added by an admin.
