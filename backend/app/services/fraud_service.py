"""Business logic for fraud model predictions."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from random import Random
from typing import Any

def _get_sqlalchemy_select():
    try:
        sqlalchemy_module = importlib.import_module("sqlalchemy")
        return getattr(sqlalchemy_module, "select")
    except Exception as exc:
        raise ImportError("sqlalchemy is required for fraud service") from exc


Session = Any

from app.models.claim import Claim
from app.models.fraud_prediction import FraudPrediction

_rng = Random(42)


class FraudService:
    def __init__(self, db: Any) -> None:
        self.db = db

    def predict_for_claim(self, claim_id: int) -> FraudPrediction:
        claim = self.db.get(Claim, claim_id)
        if claim is None:
            raise ValueError("Claim not found")

        ensemble_score = min(1.0, max(0.0, (claim.claim_amount / 100000.0) + _rng.uniform(0.05, 0.35)))
        fusion_score = min(1.0, max(0.0, ensemble_score + _rng.uniform(-0.05, 0.08)))
        shap_values = {
            "claim_amount": round(ensemble_score * 0.33, 4),
            "accident_date_recency": round(_rng.uniform(-0.08, 0.18), 4),
            "policy_pattern": round(_rng.uniform(-0.05, 0.12), 4),
        }

        prediction = FraudPrediction(
            claim_id=claim_id,
            ensemble_score=ensemble_score,
            fusion_score=fusion_score,
            shap_values=shap_values,
            created_at=datetime.now(UTC),
        )
        claim.fraud_score = fusion_score
        claim.status = "under_review" if fusion_score >= 0.35 else "submitted"

        self.db.add(prediction)
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def get_latest_prediction(self, claim_id: int) -> FraudPrediction | None:
        select = _get_sqlalchemy_select()
        stmt = (
            select(FraudPrediction)
            .where(FraudPrediction.claim_id == claim_id)
            .order_by(FraudPrediction.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def batch_predict(self, claim_ids: list[int]) -> list[FraudPrediction]:
        outputs: list[FraudPrediction] = []
        for claim_id in claim_ids:
            outputs.append(self.predict_for_claim(claim_id))
        return outputs
