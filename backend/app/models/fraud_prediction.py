"""Fraud prediction model."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FraudPrediction(Base):
	__tablename__ = "fraud_predictions"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True, nullable=False)
	ensemble_score: Mapped[float] = mapped_column(Float, nullable=False)
	fusion_score: Mapped[float | None] = mapped_column(Float, nullable=True)
	shap_values: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

	claim = relationship("Claim", back_populates="predictions")

