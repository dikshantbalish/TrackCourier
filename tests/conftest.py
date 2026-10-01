import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SESSION_SECRET"] = "test-only-session-secret-that-is-at-least-32-characters"
os.environ["SESSION_COOKIE_SECURE"] = "false"
os.environ["CORS_ORIGINS"] = "http://testserver,http://localhost:5500"
os.environ["ENVIRONMENT"] = "test"

from app.database.connection import Base, SessionLocal, engine
from app.main import app
from app.models import AdminUser, Shipment, TrackingEvent
from app.services.authentication import hash_password


@pytest.fixture(scope="session", autouse=True)
def create_test_schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def clear_database() -> None:
    with SessionLocal() as database:
        database.execute(delete(TrackingEvent))
        database.execute(delete(Shipment))
        database.execute(delete(AdminUser))
        database.commit()


@pytest.fixture(autouse=True)
def clean_database():
    clear_database()
    yield
    clear_database()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_account():
    with SessionLocal() as database:
        admin = AdminUser(
            username="operator",
            password_hash=hash_password("a-test-password-with-12-chars"),
        )
        database.add(admin)
        database.commit()
        database.refresh(admin)
        return admin
