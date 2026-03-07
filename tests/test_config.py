"""Shared test configuration for unit/integration/security/performance suites."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestSettings:
    project_root: Path
    backend_root: Path
    frontend_root: Path
    test_database_url: str
    mock_groq_enabled: bool
    mock_ml_models: bool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"

SETTINGS = TestSettings(
    project_root=PROJECT_ROOT,
    backend_root=BACKEND_ROOT,
    frontend_root=FRONTEND_ROOT,
    test_database_url=os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:"),
    mock_groq_enabled=os.getenv("MOCK_GROQ", "1") == "1",
    mock_ml_models=os.getenv("MOCK_ML_MODELS", "1") == "1",
)


def apply_test_environment() -> None:
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("DATABASE_URL", SETTINGS.test_database_url)
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
    os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
    os.environ.setdefault("REQUIRE_HTTPS", "false")


apply_test_environment()


class MockGroqClient:
    def generate(self, **_kwargs):
        return (
            "Executive Summary:\nMock response\n\n"
            "Evidence Review:\nMock evidence\n\n"
            "SHAP Insights:\nMock SHAP\n\n"
            "Recommendation:\n- Manual review\n\n"
            "Next Steps:\n- Verify claim details\n\n"
            "Disclaimer:\nThis report is AI-generated and should be reviewed by a qualified insurance professional"
        )


class MockMLModels:
    def predict_tabular(self, *_args, **_kwargs):
        return {"fraud_score": 0.42}

    def predict_image(self, *_args, **_kwargs):
        return {"severity_score": 0.37, "affected_parts": ["bumper"]}
