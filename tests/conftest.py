import os
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///./test_forging.db"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.main import create_app

# Create isolated test database engine
test_engine = create_engine(
    "sqlite:///./test_forging.db",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes and tears down the test database schema."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_forging.db"):
        try:
            os.remove("./test_forging.db")
        except Exception:
            pass


@pytest.fixture
def db():
    """Provides a transactional database session rolled back after each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    """Provides a TestClient with overridden get_db dependency."""
    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def superadmin_user(db):
    """Creates a known active superadmin user for testing."""
    existing = db.query(User).filter(User.email == "supertest@forgingcms.com").first()
    if existing:
        return existing

    user = User(
        email="supertest@forgingcms.com",
        hashed_password=hash_password("SuperSecret@123"),
        full_name="Test Super Admin",
        role=UserRole.SUPER_ADMIN.value,
        is_active=True,
        is_superuser=True,
        failed_login_attempts=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
