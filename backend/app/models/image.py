"""Claim image model."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Image(Base):
	__tablename__ = "images"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True, nullable=False)
	filename: Mapped[str] = mapped_column(String(512), nullable=False)
	processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	damage_results: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

	claim = relationship("Claim", back_populates="images")

