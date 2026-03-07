from __future__ import annotations

import io
import importlib
import json
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

try:
    from tests.test_config import SETTINGS, apply_test_environment
except ModuleNotFoundError:
    from test_config import SETTINGS, apply_test_environment

PROJECT_ROOT = SETTINGS.project_root
BACKEND_ROOT = SETTINGS.backend_root

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

apply_test_environment()

_fastapi_testclient = importlib.import_module("fastapi.testclient")
TestClient = getattr(_fastapi_testclient, "TestClient")

_sqlalchemy = importlib.import_module("sqlalchemy")
_sqlalchemy_orm = importlib.import_module("sqlalchemy.orm")
_sqlalchemy_pool = importlib.import_module("sqlalchemy.pool")
create_engine = getattr(_sqlalchemy, "create_engine")
sessionmaker = getattr(_sqlalchemy_orm, "sessionmaker")
Session = getattr(_sqlalchemy_orm, "Session")
StaticPool = getattr(_sqlalchemy_pool, "StaticPool")

api_dependencies = importlib.import_module("app.api.dependencies")
db_base = importlib.import_module("app.db.base")
app_main = importlib.import_module("app.main")
auth_service_module = importlib.import_module("app.services.auth_service")

get_db = getattr(api_dependencies, "get_db")
Base = getattr(db_base, "Base")
app = getattr(app_main, "app")
AuthService = getattr(auth_service_module, "AuthService")

engine_kwargs = {
    "connect_args": {"check_same_thread": False} if SETTINGS.test_database_url.startswith("sqlite") else {},
}
if ":memory:" in SETTINGS.test_database_url:
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(SETTINGS.test_database_url, **engine_kwargs)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db() -> Generator[Any, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client(test_db: Any) -> Generator[Any, None, None]:
    def _override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db: Any):
    service = AuthService(test_db)
    return service.register(email="user@test.com", password="T3st@Pass!", full_name="Test User", role="surveyor")


@pytest.fixture
def test_admin(test_db: Any):
    service = AuthService(test_db)
    return service.register(email="admin@test.com", password="Adm1n@Pass!", full_name="Test Admin", role="admin")


@pytest.fixture
def sample_claim_data() -> dict:
    path = PROJECT_ROOT / "fixtures" / "sample_claim_data.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "policy_number": "P-123456",
        "claim_amount": 5400.0,
        "accident_date": "2025-11-01",
        "status": "submitted",
    }


@pytest.fixture
def sample_images() -> list[tuple[str, io.BytesIO, str]]:
    return [
        ("damage_front.jpg", io.BytesIO(b"fake-jpeg-bytes-front"), "image/jpeg"),
        ("damage_rear.jpg", io.BytesIO(b"fake-jpeg-bytes-rear"), "image/jpeg"),
    ]
