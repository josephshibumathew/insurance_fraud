from __future__ import annotations

from app.models.claim import Claim


def test_db_api_claim_consistency(test_client, test_db):
    test_client.post("/api/v1/auth/register", json={"email": "consistency@test.com", "full_name": "Consistency", "password": "Consistent@123"})
    login = test_client.post("/api/v1/auth/login", json={"email": "consistency@test.com", "password": "Consistent@123"})
    token = login.json()["access_token"]

    response = test_client.post(
        "/api/v1/claims",
        data={"policy_number": "P-CONS", "claim_amount": 3210.0, "accident_date": "2025-02-15"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in {200, 201}
    claim_id = response.json()["id"]

    record = test_db.get(Claim, claim_id)
    assert record is not None
    assert record.policy_number == "P-CONS"
