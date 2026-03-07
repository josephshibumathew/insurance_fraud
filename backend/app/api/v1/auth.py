"""Authentication API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.dependencies.auth import get_current_active_user, require_role
from app.models.user import User
from app.schemas.auth import (
	AdminActivateRequest,
	AdminCreateUserRequest,
	AdminRoleRequest,
	AdminUpdatePermissionsRequest,
	AdminUpdateRoleRequest,
	ChangePasswordRequest,
	LoginResponse,
	TokenRefreshRequest,
	TokenResponse,
	UserInfo,
	UserLoginRequest,
	UserRegisterRequest,
)
from app.schemas.response import APIMessage
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
activity_logger = logging.getLogger("fraud-activity")


@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> UserInfo:
	service = AuthService(db)
	user = service.register(payload.email, payload.password, full_name=payload.full_name, role="surveyor")
	activity_logger.info("event=user_registered user_id=%s role=%s email=%s", user.id, user.role, user.email)
	return UserInfo.model_validate(service.serialize_user(user))


@router.post("/login", response_model=LoginResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
	service = AuthService(db)
	token_data = service.login(payload.email, payload.password)
	serialized = token_data.get("user") or {}
	activity_logger.info("event=user_login user_id=%s role=%s email=%s", serialized.get("id"), serialized.get("role"), serialized.get("email"))
	return LoginResponse(**token_data)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: TokenRefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
	service = AuthService(db)
	token_data = service.refresh(payload.refresh_token)
	return TokenResponse(
		access_token=token_data["access_token"],
		refresh_token=token_data["refresh_token"],
		token_type=token_data["token_type"],
	)


@router.post("/logout", response_model=APIMessage)
def logout(
	authorization: str | None = Header(default=None),
	x_refresh_token: str | None = Header(default=None, alias="X-Refresh-Token"),
	db: Session = Depends(get_db),
) -> APIMessage:
	if not authorization or not authorization.lower().startswith("bearer "):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
	token = authorization.split(" ", 1)[1]
	service = AuthService(db)
	service.logout(token, refresh_token=x_refresh_token)
	activity_logger.info("event=user_logout token_present=%s refresh_token_present=%s", True, bool(x_refresh_token))
	return APIMessage(message="Logged out successfully")


@router.get("/me", response_model=UserInfo)
def me(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)) -> UserInfo:
	service = AuthService(db)
	return UserInfo.model_validate(service.serialize_user(current_user))


@router.put("/change-password", response_model=APIMessage)
def change_password(
	payload: ChangePasswordRequest,
	current_user: User = Depends(get_current_active_user),
	db: Session = Depends(get_db),
) -> APIMessage:
	service = AuthService(db)
	service.change_password(current_user, payload.old_password, payload.new_password)
	activity_logger.info("event=password_changed user_id=%s role=%s", current_user.id, current_user.role)
	return APIMessage(message="Password updated successfully")


@admin_router.get("/users", response_model=list[UserInfo])
def list_users(_admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
	service = AuthService(db)
	return [UserInfo.model_validate(service.serialize_user(user)) for user in service.list_users()]


@admin_router.post("/users", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def create_user(payload: AdminCreateUserRequest, _admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
	service = AuthService(db)
	user = service.register(payload.email, payload.password, full_name=payload.full_name, role=payload.role, is_active=payload.is_active)
	return UserInfo.model_validate(service.serialize_user(user))


@admin_router.put("/users/{user_id}/role", response_model=UserInfo)
def update_user_role(user_id: int, payload: AdminUpdateRoleRequest, _admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
	service = AuthService(db)
	user = service.update_user_role(user_id, payload.role)
	return UserInfo.model_validate(service.serialize_user(user))


@admin_router.put("/users/{user_id}/activate/deactivate", response_model=UserInfo)
def set_user_active(user_id: int, payload: AdminActivateRequest, _admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
	service = AuthService(db)
	user = service.set_user_active(user_id, payload.is_active)
	return UserInfo.model_validate(service.serialize_user(user))


@admin_router.delete("/users/{user_id}", response_model=APIMessage)
def delete_user(user_id: int, _admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
	service = AuthService(db)
	service.delete_user(user_id)
	return APIMessage(message="User deleted")


@admin_router.get("/roles")
def list_roles(_admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
	service = AuthService(db)
	roles = service.list_roles()
	return [{"id": role.id, "name": role.name, "permissions": role.permissions} for role in roles]


@admin_router.post("/roles")
def create_role(payload: AdminRoleRequest, _admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
	service = AuthService(db)
	role = service.create_role(payload.name, payload.permissions)
	return {"id": role.id, "name": role.name, "permissions": role.permissions}


@admin_router.put("/roles/{role_id}/permissions")
def update_role_permissions(payload: AdminUpdatePermissionsRequest, role_id: int, _admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
	service = AuthService(db)
	role = service.update_role_permissions(role_id, payload.permissions)
	return {"id": role.id, "name": role.name, "permissions": role.permissions}

