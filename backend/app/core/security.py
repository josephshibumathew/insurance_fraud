"""Security utilities: hashing, JWT and role checks."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
TOKEN_BLACKLIST: set[str] = set()

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,128}$")


def verify_password(plain_password: str, hashed_password: str) -> bool:
	return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
	if not validate_password_strength(password):
		raise ValueError("Password must be 8+ chars and include letters, numbers, and symbols.")
	return pwd_context.hash(password)


def validate_password_strength(password: str) -> bool:
	return bool(PASSWORD_PATTERN.match(password or ""))


def create_access_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
	settings = get_settings()
	expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_access_token_expires_minutes))
	payload = {"sub": subject, "role": role, "type": "access", "exp": expire}
	payload.update({"iss": settings.jwt_issuer, "aud": settings.jwt_audience, "iat": datetime.now(UTC)})
	return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
	settings = get_settings()
	expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_refresh_token_expires_minutes))
	payload = {"sub": subject, "role": role, "type": "refresh", "exp": expire}
	payload.update({"iss": settings.jwt_issuer, "aud": settings.jwt_audience, "iat": datetime.now(UTC)})
	return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
	settings = get_settings()
	if token in TOKEN_BLACKLIST:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalidated")
	try:
		return jwt.decode(
			token,
			settings.jwt_secret_key,
			algorithms=[settings.jwt_algorithm],
			audience=settings.jwt_audience,
			issuer=settings.jwt_issuer,
		)
	except JWTError as exc:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def invalidate_token(token: str) -> None:
	TOKEN_BLACKLIST.add(token)


def is_token_blacklisted(token: str) -> bool:
	return token in TOKEN_BLACKLIST


def require_roles(*roles: str):
	"""RBAC dependency factory; role claim must match provided roles."""

	def _checker(user: dict[str, Any] = Depends(lambda: {"role": "user"})) -> dict[str, Any]:
		if user.get("role") not in roles:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
		return user

	return _checker

