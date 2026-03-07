"""Seed default users: 3 admins and 8 insurance surveyors."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.base import import_models
from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


SEED_ADMINS = [
    {"email": "admin1@frauddemo.com", "full_name": "Admin One", "password": "Admin@123!", "role": "admin"},
    {"email": "admin2@frauddemo.com", "full_name": "Admin Two", "password": "Admin@123!", "role": "admin"},
    {"email": "admin3@frauddemo.com", "full_name": "Admin Three", "password": "Admin@123!", "role": "admin"},
]

SEED_SURVEYORS = [
    {"email": "surveyor1@frauddemo.com", "full_name": "Surveyor 1", "password": "Surveyor@123!", "role": "surveyor"},
    {"email": "surveyor2@frauddemo.com", "full_name": "Surveyor 2", "password": "Surveyor@123!", "role": "surveyor"},
    {"email": "surveyor3@frauddemo.com", "full_name": "Surveyor 3", "password": "Surveyor@123!", "role": "surveyor"},
    {"email": "surveyor4@frauddemo.com", "full_name": "Surveyor 4", "password": "Surveyor@123!", "role": "surveyor"},
    {"email": "surveyor5@frauddemo.com", "full_name": "Surveyor 5", "password": "Surveyor@123!", "role": "surveyor"},
    {"email": "surveyor6@frauddemo.com", "full_name": "Surveyor 6", "password": "Surveyor@123!", "role": "surveyor"},
    {"email": "surveyor7@frauddemo.com", "full_name": "Surveyor 7", "password": "Surveyor@123!", "role": "surveyor"},
    {"email": "surveyor8@frauddemo.com", "full_name": "Surveyor 8", "password": "Surveyor@123!", "role": "surveyor"},
]


def _default_permissions_for_role(role_name: str) -> dict:
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


def _ensure_role(db, role_name: str) -> None:
    role = db.execute(text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}).first()
    if role:
        return
    db.add(Role(name=role_name, permissions=_default_permissions_for_role(role_name)))
    db.commit()


def _seed_user(db, user_payload: dict[str, str]) -> str:
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": user_payload["email"].lower()},
    ).first()

    if existing:
        return f"exists: {user_payload['email']}"

    _ensure_role(db, user_payload["role"])
    db.add(
        User(
            email=user_payload["email"].lower(),
            hashed_password=hash_password(user_payload["password"]),
            full_name=user_payload["full_name"],
            role=user_payload["role"],
            is_active=True,
        )
    )
    db.commit()
    return f"created: {user_payload['email']}"


def seed_users() -> None:
    import_models()
    db = SessionLocal()
    try:
        print("Seeding admins...")
        for payload in SEED_ADMINS:
            print(_seed_user(db, payload))

        print("Seeding surveyors...")
        for payload in SEED_SURVEYORS:
            print(_seed_user(db, payload))

        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()
