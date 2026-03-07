from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_db
from app.dependencies.auth import get_db as auth_get_db
from app.main import app
from app.db.base import Base


TEST_DB_PATH = "./test_auth.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> Generator[None, None, None]:
	Base.metadata.create_all(bind=engine)
	yield
	Base.metadata.drop_all(bind=engine)
	if os.path.exists(TEST_DB_PATH):
		os.remove(TEST_DB_PATH)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
	session = TestingSessionLocal()
	try:
		yield session
	finally:
		session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
	def _override_get_db():
		try:
			yield db_session
		finally:
			pass

	app.dependency_overrides[get_db] = _override_get_db
	app.dependency_overrides[auth_get_db] = _override_get_db
	with TestClient(app) as test_client:
		yield test_client
	app.dependency_overrides.clear()

