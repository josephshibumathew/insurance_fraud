"""Claim schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class ClaimCreateRequest(BaseModel):
	policy_number: str = Field(min_length=3, max_length=64)
	claim_amount: float = Field(gt=0)
	accident_date: date


class ClaimUpdateRequest(BaseModel):
	policy_number: str | None = Field(default=None, min_length=3, max_length=64)
	claim_amount: float | None = Field(default=None, gt=0)
	accident_date: date | None = None
	status: str | None = None


class ClaimResponse(BaseModel):
	id: int
	user_id: int
	policy_number: str
	claim_amount: float
	accident_date: date
	fraud_score: float | None
	status: str
	created_at: datetime

	model_config = {"from_attributes": True}


class ClaimListResponse(BaseModel):
	items: list[ClaimResponse]
	total: int
	page: int
	page_size: int

