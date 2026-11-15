import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from src.domain.models import Base
from src.main import app
from src.repositories import database


@pytest.fixture(autouse=True)
def no_external_webhooks(monkeypatch):
    monkeypatch.delenv("ANTIFRAUD_WEBHOOK_URL", raising=False)


@pytest.fixture
def db():
    engine = database.make_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with sessionmaker(bind=engine, expire_on_commit=False)() as session:
            yield session
    finally:
        engine.dispose()


@pytest.fixture
def api_store(tmp_path, monkeypatch):
    engine = database.make_engine(f"sqlite:///{(tmp_path / 'wallet.db').as_posix()}")
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessions)
    try:
        yield engine, sessions
    finally:
        engine.dispose()


@pytest.fixture
def client(api_store):
    with TestClient(app) as test_client:
        yield test_client
