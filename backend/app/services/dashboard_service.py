"""Dashboard analytics service."""

from __future__ import annotations

import importlib
from datetime import datetime
from typing import Any

def _get_sqlalchemy_helpers():
    try:
        sqlalchemy_module = importlib.import_module("sqlalchemy")
        return getattr(sqlalchemy_module, "func"), getattr(sqlalchemy_module, "select")
    except Exception as exc:
        raise ImportError("sqlalchemy is required for dashboard service") from exc


Session = Any

from app.models.claim import Claim
from app.models.report import Report


class DashboardService:
    def __init__(self, db: Any) -> None:
        self.db = db

    def get_stats(self, owner_user_id: int | None = None) -> dict:
        func, select = _get_sqlalchemy_helpers()
        total_claims_stmt = select(func.count(Claim.id))
        high_risk_stmt = select(func.count(Claim.id)).where((Claim.fraud_score.is_not(None)) & (Claim.fraud_score >= 0.7))

        if owner_user_id is not None:
            total_claims_stmt = total_claims_stmt.where(Claim.user_id == owner_user_id)
            high_risk_stmt = high_risk_stmt.where(Claim.user_id == owner_user_id)

        total_claims = int(self.db.execute(total_claims_stmt).scalar_one() or 0)
        high_risk_count = int(
            self.db.execute(high_risk_stmt).scalar_one()
            or 0
        )

        reports_stmt = select(func.count(Report.id))
        if owner_user_id is not None:
            reports_stmt = reports_stmt.join(Claim, Report.claim_id == Claim.id).where(Claim.user_id == owner_user_id)
        reports_generated = int(self.db.execute(reports_stmt).scalar_one() or 0)

        fraud_rate = (high_risk_count / total_claims) if total_claims > 0 else 0.0
        return {
            "total_claims": total_claims,
            "fraud_rate": round(fraud_rate, 4),
            "high_risk_count": high_risk_count,
            "reports_generated": reports_generated,
        }

    def get_trends(self, owner_user_id: int | None = None) -> list[dict]:
        _func, select = _get_sqlalchemy_helpers()
        stmt = select(Claim)
        if owner_user_id is not None:
            stmt = stmt.where(Claim.user_id == owner_user_id)
        claims = list(self.db.execute(stmt).scalars().all())
        bucket: dict[str, dict[str, int]] = {}
        for claim in claims:
            day = claim.created_at.date().isoformat()
            bucket.setdefault(day, {"total_claims": 0, "fraud_count": 0})
            bucket[day]["total_claims"] += 1
            if (claim.fraud_score or 0.0) >= 0.7:
                bucket[day]["fraud_count"] += 1
        return [{"date": k, **v} for k, v in sorted(bucket.items())]

    def get_high_risk_claims(self, owner_user_id: int | None = None) -> list[Claim]:
        _func, select = _get_sqlalchemy_helpers()
        stmt = select(Claim).where((Claim.fraud_score.is_not(None)) & (Claim.fraud_score >= 0.7)).order_by(Claim.created_at.desc())
        if owner_user_id is not None:
            stmt = stmt.where(Claim.user_id == owner_user_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_recent_activity(self, owner_user_id: int | None = None) -> list[dict]:
        _func, select = _get_sqlalchemy_helpers()
        stmt = select(Claim).order_by(Claim.created_at.desc()).limit(20)
        if owner_user_id is not None:
            stmt = select(Claim).where(Claim.user_id == owner_user_id).order_by(Claim.created_at.desc()).limit(20)
        claims = list(self.db.execute(stmt).scalars().all())
        return [
            {
                "claim_id": c.id,
                "status": c.status,
                "fraud_score": c.fraud_score,
                "timestamp": c.created_at.isoformat() if isinstance(c.created_at, datetime) else str(c.created_at),
            }
            for c in claims
        ]
