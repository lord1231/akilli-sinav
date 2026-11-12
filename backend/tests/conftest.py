import pytest

from app.core.rate_limit import limiter

from app.db.session import Base, engine
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
