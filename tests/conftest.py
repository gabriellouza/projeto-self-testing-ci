import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from src.domain.models import Base
from src.main import app
from src.repositories.database import get_db, make_engine


@pytest.fixture
def db():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
