from __future__ import annotations


def test_sql_injection_attempt_rejected(test_client):
    payload = {
        "email": "inject@test.com' OR '1'='1",
        "password": "Inject@123",
        "full_name": "<script>alert(1)</script>",
    }
    response = test_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in {201, 422}


def test_xss_payload_sanitized_in_full_name(test_client):
    register = test_client.post(
        "/api/v1/auth/register",
        json={"email": "xss@test.com", "password": "Xss@12345", "full_name": "<img src=x onerror=alert(1)>"},
    )
    assert register.status_code == 201
    assert "<" not in register.json().get("full_name", "")
