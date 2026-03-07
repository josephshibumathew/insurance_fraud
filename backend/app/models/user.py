"""User database model."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
	hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
	full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
	role: Mapped[str] = mapped_column(String(32), default="surveyor", nullable=False)
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
	last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	claims = relationship("Claim", back_populates="user", cascade="all, delete-orphan")
	sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

