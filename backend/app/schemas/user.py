"""User schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
	id: int
	email: EmailStr
	full_name: str | None
	role: str
	is_active: bool
	created_at: datetime
	last_login: datetime | None

	model_config = {"from_attributes": True}

