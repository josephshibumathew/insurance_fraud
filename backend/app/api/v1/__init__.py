"""Versioned API router registration."""

from fastapi import APIRouter

from .admin import router as admin_data_router
from .auth import admin_router, router as auth_router
from .claims import router as claims_router
from .dashboard import router as dashboard_router
from .fraud_detection import router as fraud_router
from .image_processing import router as image_router
from .reports import router as reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(admin_data_router)
api_router.include_router(claims_router)
api_router.include_router(fraud_router)
api_router.include_router(image_router)
api_router.include_router(reports_router)
api_router.include_router(dashboard_router)

