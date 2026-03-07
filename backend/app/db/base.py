"""SQLAlchemy metadata base and model imports."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
	pass


def import_models() -> None:
	"""Register all ORM models with SQLAlchemy metadata."""
	from app.models.claim import Claim  # noqa: F401
	from app.models.fraud_prediction import FraudPrediction  # noqa: F401
	from app.models.image import Image  # noqa: F401
	from app.models.permission import Permission  # noqa: F401
	from app.models.report import Report  # noqa: F401
	from app.models.role import Role  # noqa: F401
	from app.models.session import Session  # noqa: F401
	from app.models.user import User  # noqa: F401

