"""Database engine and session configuration."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine_kwargs = {
	"pool_pre_ping": True,
	"connect_args": {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
}

if not settings.database_url.startswith("sqlite"):
	engine_kwargs["pool_size"] = settings.db_pool_size
	engine_kwargs["max_overflow"] = settings.db_max_overflow

engine = create_engine(settings.database_url, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

