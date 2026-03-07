from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    invalidate_token,
    is_token_blacklisted,
    validate_password_strength,
    verify_password,
)


def test_password_hash_and_verify():
    password = "Secure@123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_password_strength_rules():
    assert validate_password_strength("Good@123")
    assert not validate_password_strength("weakpass")


def test_token_create_decode_and_blacklist():
    token = create_access_token("1", "surveyor", expires_delta=timedelta(minutes=5))
    payload = decode_token(token)
    assert payload["sub"] == "1"

    invalidate_token(token)
    assert is_token_blacklisted(token)
    with pytest.raises(Exception):
        decode_token(token)
