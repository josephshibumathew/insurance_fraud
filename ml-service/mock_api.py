from __future__ import annotations

from fastapi import FastAPI, File, UploadFile

app = FastAPI(title="Local ML Mock Service", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict/fraud")
def predict_fraud(payload: dict) -> dict:
    claim_amount = float(payload.get("claim_amount", 0) or 0)
    ensemble_score = min(1.0, max(0.0, claim_amount / 100000.0 + 0.15))
    fusion_score = min(1.0, max(0.0, ensemble_score + 0.03))
    return {
        "fraud_score": fusion_score,
        "ensemble_score": ensemble_score,
        "fusion_score": fusion_score,
        "shap_values": {
            "claim_amount": round(ensemble_score * 0.35, 4),
            "policy_pattern": 0.06,
            "accident_date_recency": 0.02,
        },
    }


@app.post("/predict/damage")
async def predict_damage(image: UploadFile = File(...)) -> dict:
    _ = await image.read()
    return {
        "bounding_boxes": [{"x": 28, "y": 34, "w": 90, "h": 68, "label": "damage", "confidence": 0.89}],
        "severity_score": 0.62,
        "affected_parts": ["bumper", "door"],
        "detection_count": 1,
    }