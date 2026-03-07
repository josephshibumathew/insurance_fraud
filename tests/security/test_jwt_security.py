from __future__ import annotations


def test_jwt_tampering_detected(test_client):
    test_client.post("/api/v1/auth/register", json={"email": "jwt@test.com", "full_name": "JWT User", "password": "Jwt@12345"})
    login = test_client.post("/api/v1/auth/login", json={"email": "jwt@test.com", "password": "Jwt@12345"}).json()
    token = login["access_token"]

    tampered = token + "tamper"
    response = test_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert response.status_code == 401
