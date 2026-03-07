from __future__ import annotations


def test_multistep_upload_predict_report_workflow(test_client, sample_images):
    test_client.post("/api/v1/auth/register", json={"email": "multi@test.com", "full_name": "Multi User", "password": "Mult1@Pass"})
    login = test_client.post("/api/v1/auth/login", json={"email": "multi@test.com", "password": "Mult1@Pass"})
    token = login.json()["access_token"]

    claim = test_client.post(
        "/api/v1/claims",
        data={"policy_number": "P-MULTI", "claim_amount": 2500.0, "accident_date": "2025-03-01"},
        headers={"Authorization": f"Bearer {token}"},
    )
    claim_id = claim.json()["id"]

    img = sample_images[0]
    image_upload = test_client.post(
        f"/api/v1/claims/{claim_id}/images",
        files={"image_file": (img[0], img[1].getvalue(), img[2])},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert image_upload.status_code in {200, 201}

    pred = test_client.post("/api/v1/fraud/predict", json={"claim_id": claim_id}, headers={"Authorization": f"Bearer {token}"})
    assert pred.status_code == 200

    report = test_client.post(f"/api/v1/reports/generate/{claim_id}", headers={"Authorization": f"Bearer {token}"})
    assert report.status_code in {200, 201}
