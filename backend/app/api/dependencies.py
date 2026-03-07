"""Shared FastAPI dependencies."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_active_user
from app.db.session import SessionLocal


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


def get_current_user(current_user=Depends(get_current_active_user)):
	return current_user


@lru_cache
def get_ml_models() -> dict[str, Any]:
	"""Resolve model handles used by fraud and image endpoints."""
	return {
		"ensemble": "loaded_or_stub_ensemble_model",
		"yolo": "loaded_or_stub_yolo_model",
		"fusion": "loaded_or_stub_fusion_model",
		"shap": "loaded_or_stub_shap_explainer",
	}

