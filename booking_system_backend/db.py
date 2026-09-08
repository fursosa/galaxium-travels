import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base

# Get database URL from environment, fallback to SQLite for local dev
SQLALCHEMY_DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'sqlite:///./booking.db'
)

# PostgreSQL doesn't need check_same_thread
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith('sqlite'):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all database tables defined in the ORM models.

    Safe to call on every startup — SQLAlchemy only creates tables that
    don't already exist (``CREATE TABLE IF NOT EXISTS`` semantics).
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session per request.

    Opens a ``SessionLocal`` session, yields it to the route handler, and
    closes it in the ``finally`` block regardless of whether the handler
    raised an exception.  Use this with ``Depends(get_db)`` in route
    signatures.

    Yields:
        Session: An active SQLAlchemy ORM session bound to ``engine``.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()