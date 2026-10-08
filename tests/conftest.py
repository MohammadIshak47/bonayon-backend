import os

import pytest

from sqlalchemy.engine import make_url  # noqa: E402

_url = os.environ.get("TEST_DATABASE_URL")
if not _url or "test" not in (make_url(_url).database or ""):
    pytest.exit("Set TEST_DATABASE_URL to a PostgreSQL database whose NAME contains 'test' (tests drop and recreate tables).", returncode=2)
os.environ["DATABASE_URL"] = _url
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-12345")
os.environ["CLIMATE_PROVIDER"] = "mock"

import app.models  # noqa: E402,F401
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api.deps import get_climate_provider  # noqa: E402
from app.core.db import Base, engine, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.integrations.mock_provider import MockProvider  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402
from scripts import seed_crops, seed_districts  # noqa: E402

PASSWORD = "Password123"


@pytest.fixture(scope="session", autouse=True)
def schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    """Each test runs in a transaction that is rolled back, so tests never see each other's data."""
    conn = engine.connect()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False, expire_on_commit=False)
    yield session
    session.close()
    trans.rollback()
    conn.close()


@pytest.fixture
def seeded(db):
    seed_districts.seed(db)
    seed_crops.seed(db)
    return db


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_climate_provider] = lambda: MockProvider()
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, email: str, role: Role = Role.farmer, active: bool = True) -> User:
    u = User(name=email.split("@")[0], email=email, phone=None, password_hash=hash_password(PASSWORD), role=role, is_active=active)
    db.add(u)
    db.commit()
    return u


def login(client, email: str) -> dict:
    r = client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def farmer(db, client):
    make_user(db, "farmer@example.com")
    return login(client, "farmer@example.com")


@pytest.fixture
def other_farmer(db, client):
    make_user(db, "other@example.com")
    return login(client, "other@example.com")


@pytest.fixture
def admin(db, client):
    make_user(db, "admin@example.com", Role.admin)
    return login(client, "admin@example.com")


def district_id(client, name="Dhaka") -> str:
    return next(d["id"] for d in client.get("/api/v1/districts").json() if d["name_en"] == name)


def crop_id(client, headers, name) -> str:
    return next(c["id"] for c in client.get("/api/v1/crops", headers=headers).json() if c["name_en"] == name)
