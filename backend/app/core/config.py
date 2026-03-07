"""Application configuration settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	"""Runtime settings loaded from environment variables."""

	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

	app_name: str = "Automobile Insurance Fraud Detection API"
	app_description: str = "Comprehensive backend for claims, fraud scoring, damage analysis, and AI reports."
	app_version: str = "1.0.0"
	environment: Literal["development", "staging", "production", "test"] = "development"

	backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])

	database_url: str = "sqlite:///./backend.db"
	db_pool_size: int = 10
	db_max_overflow: int = 20

	jwt_secret_key: str = "change-this-secret"
	jwt_algorithm: str = "HS256"
	jwt_access_token_expires_minutes: int = 30
	jwt_refresh_token_expires_minutes: int = 60 * 24 * 7
	jwt_issuer: str = "fraud-platform"
	jwt_audience: str = "fraud-dashboard"

	auth_max_login_attempts: int = 5
	auth_lockout_minutes: int = 15
	require_https: bool = False

	groq_api_key: str | None = None
	groq_model: str = "llama3-70b-8192"

	ml_api_url: str | None = None  # HF Space inference URL, e.g. https://user-space.hf.space

	rate_limit_per_minute: int = 120
	request_id_header: str = "X-Request-ID"

	uploads_dir: str = "uploads"
	reports_dir: str = "artifacts/reports"
	logs_dir: str = "logs"
	api_log_file: str = "api.log"
	activity_log_file: str = "activity.log"
	system_log_file: str = "system.log"


@lru_cache
def get_settings() -> Settings:
	return Settings()

