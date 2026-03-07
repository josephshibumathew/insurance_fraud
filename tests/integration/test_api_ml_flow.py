from __future__ import annotations


def test_api_ml_end_to_end_flow(test_client, sample_claim_data):
    register = test_client.post(
        "/api/v1/auth/register",
        json={"email": "flow@test.com", "full_name": "Flow User", "password": "Flow@1234"},
    )
    assert register.status_code == 201

    login = test_client.post("/api/v1/auth/login", json={"email": "flow@test.com", "password": "Flow@1234"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    claim = test_client.post(
        "/api/v1/claims",
        data={
            "policy_number": sample_claim_data["policy_number"],
            "claim_amount": sample_claim_data["claim_amount"],
            "accident_date": sample_claim_data["accident_date"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert claim.status_code in {200, 201}
    claim_id = claim.json()["id"]

    pred = test_client.post("/api/v1/fraud/predict", json={"claim_id": claim_id}, headers={"Authorization": f"Bearer {token}"})
    assert pred.status_code == 200

    report = test_client.post(f"/api/v1/reports/generate/{claim_id}", headers={"Authorization": f"Bearer {token}"})
    assert report.status_code in {200, 201}
