import os

import pytest
from fastapi.testclient import TestClient

os.environ["ATLAS_DATABASE_URL"] = "sqlite:///./atlasagent-test.db"
os.environ["ATLAS_APPROVAL_SECRET"] = "test-secret"

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

