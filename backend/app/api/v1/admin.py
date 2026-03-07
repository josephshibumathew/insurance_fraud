"""Admin analytics and system management endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.dependencies.auth import require_role
from app.models.claim import Claim
from app.models.report import Report
from app.models.user import User
from app.services.log_service import LogService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard/stats")
def admin_dashboard_stats(_admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    total_claims = int(db.execute(select(func.count(Claim.id))).scalar_one() or 0)
    high_risk = int(
        db.execute(select(func.count(Claim.id)).where((Claim.fraud_score.is_not(None)) & (Claim.fraud_score >= 0.7))).scalar_one() or 0
    )
    fraud_rate = (high_risk / total_claims) if total_claims else 0.0
    surveyor_count = int(db.execute(select(func.count(User.id)).where(User.role == "surveyor")).scalar_one() or 0)
    reports_count = int(db.execute(select(func.count(Report.id))).scalar_one() or 0)

    recent_claims = list(db.execute(select(Claim).order_by(Claim.created_at.desc()).limit(10)).scalars().all())

    return {
        "total_claims": total_claims,
        "fraud_rate": round(fraud_rate, 4),
        "high_risk_count": high_risk,
        "surveyor_count": surveyor_count,
        "reports_generated": reports_count,
        "recent_activity": [
            {
                "claim_id": claim.id,
                "user_id": claim.user_id,
                "status": claim.status,
                "fraud_score": claim.fraud_score,
                "created_at": claim.created_at,
            }
            for claim in recent_claims
        ],
    }


@router.get("/logs")
def admin_logs(
    lines: int = Query(default=200, ge=10, le=1000),
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    log_map = {
        "api": Path(settings.logs_dir) / settings.api_log_file,
        "activity": Path(settings.logs_dir) / settings.activity_log_file,
        "system": Path(settings.logs_dir) / settings.system_log_file,
    }

    surveyors = list(db.execute(select(User).where(User.role == "surveyor").order_by(User.created_at.desc())).scalars().all())
    surveyor_details = []
    for surveyor in surveyors:
        claims_count = int(db.execute(select(func.count(Claim.id)).where(Claim.user_id == surveyor.id)).scalar_one() or 0)
        surveyor_details.append(
            {
                "id": surveyor.id,
                "email": surveyor.email,
                "full_name": surveyor.full_name,
                "is_active": surveyor.is_active,
                "created_at": surveyor.created_at,
                "last_login": surveyor.last_login,
                "total_claims": claims_count,
            }
        )

    config_path = Path("ml_models/config/model_config.yaml")
    models = {
        "ensemble_model": {
            "name": "Weighted Ensemble",
            "path": "ml_models/ensemble/weighted_ensemble.py",
            "version": "v1",
        },
        "yolo_model": {
            "name": "YOLOv11",
            "path": "yolo11n.pt",
            "version": "11n",
        },
        "preprocessor": {
            "path": "ml_models/data/preprocessing.py",
            "status": "active",
        },
        "config_file_exists": config_path.exists(),
        "config_file": str(config_path),
    }

    grouped_logs = LogService.collect_named_logs(log_map=log_map, lines=lines)
    return {
        "logs": grouped_logs,
        "log_files": {name: str(path) for name, path in log_map.items()},
        "surveyor_count": len(surveyor_details),
        "surveyors": surveyor_details,
        "ml_models": models,
        "environment": settings.environment,
        "requested_lines": lines,
    }


@router.get("/ml-models")
def admin_ml_models(_admin: User = Depends(require_role("admin"))):
    config_path = Path("ml_models/config/model_config.yaml")
    return {
        "ensemble_model": {
            "name": "Weighted Ensemble",
            "path": "ml_models/ensemble/weighted_ensemble.py",
            "version": "v1",
        },
        "yolo_model": {
            "name": "YOLOv11",
            "path": "yolo11n.pt",
            "version": "11n",
        },
        "preprocessor": {
            "path": "ml_models/data/preprocessing.py",
            "status": "active",
        },
        "last_training_date": None,
        "config_file_exists": config_path.exists(),
        "config_file": str(config_path),
    }


@router.get("/surveyors")
def admin_surveyors(_admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    surveyors = list(db.execute(select(User).where(User.role == "surveyor").order_by(User.created_at.desc())).scalars().all())

    output = []
    for surveyor in surveyors:
        claims_count = int(db.execute(select(func.count(Claim.id)).where(Claim.user_id == surveyor.id)).scalar_one() or 0)
        output.append(
            {
                "id": surveyor.id,
                "email": surveyor.email,
                "full_name": surveyor.full_name,
                "created_at": surveyor.created_at,
                "total_claims": claims_count,
            }
        )

    return output


@router.get("/claims")
def admin_claims(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    stmt = select(Claim).order_by(Claim.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    claims = list(db.execute(stmt).scalars().all())
    total = int(db.execute(select(func.count(Claim.id))).scalar_one() or 0)
    return {
        "items": [
            {
                "id": claim.id,
                "user_id": claim.user_id,
                "policy_number": claim.policy_number,
                "claim_amount": claim.claim_amount,
                "accident_date": claim.accident_date,
                "fraud_score": claim.fraud_score,
                "status": claim.status,
                "created_at": claim.created_at,
            }
            for claim in claims
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/reports")
def admin_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    stmt = select(Report).order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    reports = list(db.execute(stmt).scalars().all())
    total = int(db.execute(select(func.count(Report.id))).scalar_one() or 0)

    return {
        "items": [
            {
                "id": report.id,
                "claim_id": report.claim_id,
                "pdf_path": report.pdf_path,
                "created_at": report.created_at,
            }
            for report in reports
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
