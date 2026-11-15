import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.domain.models import Base


def make_engine(url=None):
    url = url or os.getenv("DATABASE_URL", "sqlite:///./wallet.db")
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    if url == "sqlite://":
        kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=10000")
            cursor.close()
    return engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db(target_engine=None):
    Base.metadata.create_all(target_engine or engine)


def get_db():
    with SessionLocal() as db:
        yield db
