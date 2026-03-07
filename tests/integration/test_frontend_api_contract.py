from __future__ import annotations

from pathlib import Path


def test_frontend_api_contract_contains_required_endpoints():
    api_js = Path("frontend/src/services/api.js").read_text(encoding="utf-8")
    required = [
        "/auth/login",
        "/claims",
        "/fraud/predict",
        "/reports/generate",
        "/dashboard/stats",
    ]
    for endpoint in required:
        assert endpoint in api_js
