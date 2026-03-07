"""Generated report model."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Report(Base):
	__tablename__ = "reports"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True, nullable=False)
	pdf_path: Mapped[str] = mapped_column(String(1024), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

	claim = relationship("Claim", back_populates="reports")

