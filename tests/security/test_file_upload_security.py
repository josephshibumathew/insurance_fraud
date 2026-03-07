from __future__ import annotations


def test_malicious_file_upload_handled(test_client):
    test_client.post("/api/v1/auth/register", json={"email": "file@test.com", "full_name": "File User", "password": "File@12345"})
    login = test_client.post("/api/v1/auth/login", json={"email": "file@test.com", "password": "File@12345"})
    token = login.json()["access_token"]

    claim = test_client.post(
        "/api/v1/claims",
        data={"policy_number": "P-FILE", "claim_amount": 1100, "accident_date": "2025-03-05"},
        headers={"Authorization": f"Bearer {token}"},
    )
    claim_id = claim.json()["id"]

    response = test_client.post(
        f"/api/v1/claims/{claim_id}/images",
        files={"image_file": ("malicious.exe", b"MZ fake binary", "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in {200, 201, 400, 415}
