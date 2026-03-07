from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.auth import ChangePasswordRequest, UserLoginRequest, UserRegisterRequest
from app.schemas.claim import ClaimCreateRequest


def test_auth_schema_validation_success():
    payload = UserRegisterRequest(email="valid@example.com", password="Strong@123", full_name="Valid User")
    assert payload.email == "valid@example.com"


def test_auth_schema_validation_failure():
    with pytest.raises(ValidationError):
        UserLoginRequest(email="broken-email", password="123")


def test_change_password_schema():
    payload = ChangePasswordRequest(old_password="Old@1234", new_password="New@1234")
    assert payload.new_password.startswith("New")


def test_claim_schema_validation():
    payload = ClaimCreateRequest(policy_number="P-1234", claim_amount=1000.0, accident_date="2025-01-01")
    assert payload.claim_amount == 1000.0
