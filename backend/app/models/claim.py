"""Claim database model."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Claim(Base):
	__tablename__ = "claims"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	policy_number: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
	claim_amount: Mapped[float] = mapped_column(Float, nullable=False)
	accident_date: Mapped[date] = mapped_column(Date, nullable=False)
	fraud_score: Mapped[float | None] = mapped_column(Float, nullable=True)
	status: Mapped[str] = mapped_column(String(32), default="submitted", nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

	user = relationship("User", back_populates="claims")
	images = relationship("Image", back_populates="claim", cascade="all, delete-orphan")
	predictions = relationship("FraudPrediction", back_populates="claim", cascade="all, delete-orphan")
	reports = relationship("Report", back_populates="claim", cascade="all, delete-orphan")

