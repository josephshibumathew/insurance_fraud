"""Dashboard response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    total_claims: int
    fraud_rate: float
    high_risk_count: int
    reports_generated: int


class TrendPoint(BaseModel):
    date: str
    total_claims: int
    fraud_count: int


class DashboardTrendResponse(BaseModel):
    trends: list[TrendPoint]
