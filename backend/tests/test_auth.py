from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.security import create_access_token


def test_register_valid_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "surveyor@example.com", "full_name": "Jane Surveyor", "password": "Secure@123"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "surveyor@example.com"
    assert payload["role"] == "surveyor"


def test_register_invalid_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "invalid-email", "full_name": "Bad Email", "password": "Secure@123"},
    )
    assert response.status_code == 422


def test_login_success_and_failure(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "full_name": "Login User", "password": "Secure@123"},
    )

    ok_response = client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "Secure@123"})
    assert ok_response.status_code == 200
    assert "access_token" in ok_response.json()

    bad_response = client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "Wrong@123"})
    assert bad_response.status_code == 401


def test_protected_endpoint_without_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_role_based_access_denied_for_non_admin(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "basic@example.com", "full_name": "Basic User", "password": "Secure@123"},
    )
    login = client.post("/api/v1/auth/login", json={"email": "basic@example.com", "password": "Secure@123"}).json()
    access = login["access_token"]

    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 403


def test_token_expiration_rejected(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "exp@example.com", "full_name": "Exp User", "password": "Secure@123"},
    )
    login = client.post("/api/v1/auth/login", json={"email": "exp@example.com", "password": "Secure@123"}).json()
    user_id = login["user"]["id"]

    expired_token = create_access_token(str(user_id), "surveyor", expires_delta=timedelta(seconds=-1))
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


def test_change_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "changepw@example.com", "full_name": "PW User", "password": "Secure@123"},
    )
    login = client.post("/api/v1/auth/login", json={"email": "changepw@example.com", "password": "Secure@123"}).json()
    access = login["access_token"]

    response = client.put(
        "/api/v1/auth/change-password",
        json={"old_password": "Secure@123", "new_password": "N3wSecure@456"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 200

    second_login = client.post("/api/v1/auth/login", json={"email": "changepw@example.com", "password": "N3wSecure@456"})
    assert second_login.status_code == 200
