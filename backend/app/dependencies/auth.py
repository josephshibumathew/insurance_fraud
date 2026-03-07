"""Authentication and authorization dependencies."""

from __future__ import annotations

import importlib
from typing import Any, Callable

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User

_fastapi = importlib.import_module("fastapi")
Depends = getattr(_fastapi, "Depends")
Header = getattr(_fastapi, "Header")
HTTPException = getattr(_fastapi, "HTTPException")
status = getattr(_fastapi, "status")

_sqlalchemy = importlib.import_module("sqlalchemy")
select = getattr(_sqlalchemy, "select")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization scheme")
    return parts[1]


def get_current_user(authorization: str | None = Header(default=None), db: Any = Depends(get_db)) -> User:
    token = _extract_bearer_token(authorization)
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    user_id = payload.get("sub")
    user = db.get(User, int(user_id)) if user_id else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


def require_role(role_name: str) -> Callable:
    def _checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != role_name:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return _checker


def require_permission(resource: str, action: str) -> Callable:
    def _checker(current_user: User = Depends(get_current_active_user), db: Any = Depends(get_db)) -> User:
        if current_user.role == "admin":
            return current_user

        role = db.execute(select(Role).where(Role.name == current_user.role)).scalar_one_or_none()
        permissions = (role.permissions if role else {}) or {}
        resource_actions = permissions.get(resource, [])
        if action not in resource_actions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return current_user

    return _checker
