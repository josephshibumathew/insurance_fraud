"""Shared API response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class APIMessage(BaseModel):
	message: str


class APIError(BaseModel):
	detail: str
	request_id: str | None = None


class AuditResponse(BaseModel):
	request_id: str
	timestamp: datetime
	data: dict[str, Any] | None = None

