import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import limiter

from app.db.session import Base, engine, get_db
from app import models  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
def create_test_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)



@pytest.fixture(autouse=True)
def reset_rate_limits_between_tests():
    # TestClient shares one remote address across test cases; isolate rate-limit state.
    limiter._storage.reset()
    yield


@pytest.fixture()
def factory():
    """Testler arası paylaşılmayan, bellekte izole SQLite oturum fabrikası."""
    isolated = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(isolated)
    yield sessionmaker(bind=isolated, autoflush=False, autocommit=False)
    isolated.dispose()


@pytest.fixture()
def client(factory):
    from app.main import app

    def override():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
