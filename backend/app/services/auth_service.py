"""Authentication business logic."""

from __future__ import annotations

import html
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.config import get_settings
from app.core.security import (
	create_access_token,
	create_refresh_token,
	decode_token,
	hash_password,
	invalidate_token,
	validate_password_strength,
	verify_password,
)
from app.models.role import Role
from app.models.session import Session as UserSession
from app.models.user import User


FAILED_LOGIN_ATTEMPTS: dict[str, dict[str, datetime | int]] = {}


class AuthService:
	def __init__(self, db: Session) -> None:
		self.db = db
		self.settings = get_settings()

	def _sanitize_name(self, full_name: str | None) -> str | None:
		if full_name is None:
			return None
		return html.escape(full_name.strip())[:255] or None

	def _default_permissions_for_role(self, role_name: str) -> dict:
		if role_name == "admin":
			return {"*": ["create", "read", "update", "delete"]}
		if role_name == "surveyor":
			return {
				"claims": ["create", "read", "update"],
				"fraud": ["read"],
				"reports": ["create", "read"],
				"images": ["create", "read"],
			}
		return {}

	def _ensure_role_exists(self, role_name: str) -> Role:
		role = self.db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
		if role is None:
			role = Role(name=role_name, permissions=self._default_permissions_for_role(role_name))
			self.db.add(role)
			self.db.flush()
		return role

	def _login_key(self, email: str) -> str:
		return email.lower().strip()

	def _check_lockout(self, email: str) -> None:
		key = self._login_key(email)
		entry = FAILED_LOGIN_ATTEMPTS.get(key)
		if not entry:
			return
		locked_until = entry.get("locked_until")
		if isinstance(locked_until, datetime) and locked_until > datetime.now(UTC):
			raise UnauthorizedError("Account temporarily locked due to failed attempts. Try later.")

	def _register_failed_attempt(self, email: str) -> None:
		key = self._login_key(email)
		now = datetime.now(UTC)
		entry = FAILED_LOGIN_ATTEMPTS.setdefault(key, {"count": 0, "locked_until": now})
		entry["count"] = int(entry.get("count", 0)) + 1
		if int(entry["count"]) >= self.settings.auth_max_login_attempts:
			entry["locked_until"] = now + timedelta(minutes=self.settings.auth_lockout_minutes)

	def _reset_failed_attempts(self, email: str) -> None:
		FAILED_LOGIN_ATTEMPTS.pop(self._login_key(email), None)

	def _session_expiry(self) -> datetime:
		return datetime.now(UTC) + timedelta(minutes=self.settings.jwt_refresh_token_expires_minutes)

	def _build_user_permissions(self, user: User) -> dict:
		role = self.db.execute(select(Role).where(Role.name == user.role)).scalar_one_or_none()
		return (role.permissions if role else {}) or {}

	def serialize_user(self, user: User) -> dict:
		return {
			"id": user.id,
			"email": user.email,
			"full_name": user.full_name,
			"role": user.role,
			"is_active": user.is_active,
			"created_at": user.created_at,
			"last_login": user.last_login,
			"permissions": self._build_user_permissions(user),
		}

	def register(self, email: str, password: str, full_name: str | None = None, role: str = "surveyor", is_active: bool = True) -> User:
		if not validate_password_strength(password):
			raise UnauthorizedError("Password does not meet complexity requirements")

		existing = self.db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
		if existing is not None:
			raise ConflictError("Email is already registered")

		self._ensure_role_exists(role)
		user = User(
			email=email.lower(),
			hashed_password=hash_password(password),
			full_name=self._sanitize_name(full_name),
			role=role,
			is_active=is_active,
		)
		self.db.add(user)
		self.db.commit()
		self.db.refresh(user)
		return user

	def login(self, email: str, password: str) -> dict:
		self._check_lockout(email)
		user = self.db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
		if user is None or not user.is_active or not verify_password(password, user.hashed_password):
			self._register_failed_attempt(email)
			raise UnauthorizedError("Invalid email or password")

		self._reset_failed_attempts(email)
		user.last_login = datetime.now(UTC)
		self.db.add(user)

		access_token = create_access_token(str(user.id), user.role)
		refresh_token = create_refresh_token(str(user.id), user.role)

		session = UserSession(user_id=user.id, token=refresh_token, expires_at=self._session_expiry())
		self.db.add(session)
		self.db.commit()

		return {
			"access_token": access_token,
			"refresh_token": refresh_token,
			"token_type": "bearer",
			"user": self.serialize_user(user),
		}

	def refresh(self, refresh_token: str) -> dict:
		payload = decode_token(refresh_token)
		if payload.get("type") != "refresh":
			raise UnauthorizedError("Invalid refresh token")

		user_id = payload.get("sub")
		user = self.db.get(User, int(user_id)) if user_id is not None else None
		if user is None or not user.is_active:
			raise UnauthorizedError("User not found")

		session = self.db.execute(select(UserSession).where(UserSession.token == refresh_token)).scalar_one_or_none()
		if session is None or session.expires_at < datetime.now(UTC):
			raise UnauthorizedError("Refresh token expired or invalid")

		new_access = create_access_token(str(user.id), user.role)

		return {
			"access_token": new_access,
			"refresh_token": refresh_token,
			"token_type": "bearer",
			"user": self.serialize_user(user),
		}

	def logout(self, token: str, refresh_token: str | None = None) -> None:
		invalidate_token(token)
		if refresh_token:
			invalidate_token(refresh_token)
			session = self.db.execute(select(UserSession).where(UserSession.token == refresh_token)).scalar_one_or_none()
			if session:
				self.db.delete(session)
				self.db.commit()

	def get_current_user(self, access_token: str) -> User:
		payload = decode_token(access_token)
		if payload.get("type") != "access":
			raise UnauthorizedError("Invalid access token")

		user_id = payload.get("sub")
		user = self.db.get(User, int(user_id)) if user_id is not None else None
		if user is None:
			raise UnauthorizedError("User not found")
		if not user.is_active:
			raise UnauthorizedError("Inactive user")
		return user

	def change_password(self, user: User, old_password: str, new_password: str) -> None:
		if not verify_password(old_password, user.hashed_password):
			raise UnauthorizedError("Old password is incorrect")
		if not validate_password_strength(new_password):
			raise UnauthorizedError("New password does not meet complexity requirements")
		target_user = self.db.get(User, user.id)
		if target_user is None:
			raise UnauthorizedError("User not found")
		target_user.hashed_password = hash_password(new_password)
		self.db.commit()

	def list_users(self) -> list[User]:
		return list(self.db.execute(select(User).order_by(User.created_at.desc())).scalars().all())

	def get_user(self, user_id: int) -> User | None:
		return self.db.get(User, user_id)

	def update_user_role(self, user_id: int, role_name: str) -> User:
		user = self.get_user(user_id)
		if user is None:
			raise ConflictError("User not found")
		self._ensure_role_exists(role_name)
		user.role = role_name
		self.db.add(user)
		self.db.commit()
		self.db.refresh(user)
		return user

	def set_user_active(self, user_id: int, is_active: bool) -> User:
		user = self.get_user(user_id)
		if user is None:
			raise ConflictError("User not found")
		user.is_active = is_active
		self.db.add(user)
		self.db.commit()
		self.db.refresh(user)
		return user

	def delete_user(self, user_id: int) -> None:
		user = self.get_user(user_id)
		if user is None:
			raise ConflictError("User not found")
		self.db.delete(user)
		self.db.commit()

	def list_roles(self) -> list[Role]:
		return list(self.db.execute(select(Role).order_by(Role.name.asc())).scalars().all())

	def create_role(self, name: str, permissions: dict) -> Role:
		existing = self.db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
		if existing:
			raise ConflictError("Role already exists")
		role = Role(name=name, permissions=permissions)
		self.db.add(role)
		self.db.commit()
		self.db.refresh(role)
		return role

	def update_role_permissions(self, role_id: int, permissions: dict) -> Role:
		role = self.db.get(Role, role_id)
		if role is None:
			raise ConflictError("Role not found")
		role.permissions = permissions
		self.db.add(role)
		self.db.commit()
		self.db.refresh(role)
		return role

