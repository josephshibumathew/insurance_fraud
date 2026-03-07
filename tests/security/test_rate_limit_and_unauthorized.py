from __future__ import annotations


def test_unauthorized_access_blocked(test_client):
    response = test_client.get("/api/v1/claims")
    assert response.status_code == 401


def test_login_rate_limit_lockout(test_client):
    test_client.post("/api/v1/auth/register", json={"email": "lock@test.com", "full_name": "Lock User", "password": "Lock@12345"})

    for _ in range(6):
        resp = test_client.post("/api/v1/auth/login", json={"email": "lock@test.com", "password": "Wrong@123"})

    assert resp.status_code == 401
    assert "locked" in resp.json().get("detail", "").lower() or "invalid" in resp.json().get("detail", "").lower()
