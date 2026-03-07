"""Dashboard analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.claim import ClaimResponse
from app.schemas.dashboard import DashboardStatsResponse, DashboardTrendResponse, TrendPoint
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	owner_user_id = None if current_user.role == "admin" else current_user.id
	return DashboardStatsResponse(**DashboardService(db).get_stats(owner_user_id=owner_user_id))


@router.get("/trends", response_model=DashboardTrendResponse)
def trends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	owner_user_id = None if current_user.role == "admin" else current_user.id
	points = [TrendPoint(**item) for item in DashboardService(db).get_trends(owner_user_id=owner_user_id)]
	return DashboardTrendResponse(trends=points)


@router.get("/high-risk", response_model=list[ClaimResponse])
def high_risk(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	owner_user_id = None if current_user.role == "admin" else current_user.id
	claims = DashboardService(db).get_high_risk_claims(owner_user_id=owner_user_id)
	return [ClaimResponse.model_validate(claim) for claim in claims]


@router.get("/recent-activity")
def recent_activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	owner_user_id = None if current_user.role == "admin" else current_user.id
	return {"items": DashboardService(db).get_recent_activity(owner_user_id=owner_user_id)}

