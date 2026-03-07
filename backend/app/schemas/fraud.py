"""Fraud prediction schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FraudPredictRequest(BaseModel):
    claim_id: int


class FraudResultResponse(BaseModel):
    claim_id: int
    ensemble_score: float = Field(ge=0.0, le=1.0)
    fusion_score: float | None = Field(default=None, ge=0.0, le=1.0)
    shap_values: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class FraudBatchRequest(BaseModel):
    claim_ids: list[int] = Field(default_factory=list, min_length=1)


class FraudBatchResponse(BaseModel):
    results: list[FraudResultResponse]
