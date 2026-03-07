"""API routes for AI-generated fraud reports."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.dependencies.auth import require_role
from app.models.claim import Claim
from app.models.user import User
from app.schemas.report import GenerateReportResponse, ReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def _ensure_claim_access(service: ReportService, claim_id: int, current_user: User) -> None:
	claim = service.db.get(Claim, claim_id)
	if claim is None:
		raise HTTPException(status_code=404, detail="Claim not found")
	if current_user.role != "admin" and claim.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Not authorized for this claim")


def _ensure_report_access(service: ReportService, report_id: int, current_user: User):
	report = service.get_report(report_id)
	if report is None:
		raise HTTPException(status_code=404, detail="Report not found")
	claim = service.db.get(Claim, report.claim_id)
	if claim is None:
		raise HTTPException(status_code=404, detail="Claim not found")
	if current_user.role != "admin" and claim.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Not authorized for this report")
	return report

@router.post("/generate/{claim_id}", response_model=GenerateReportResponse)
def generate_claim_report(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("surveyor"))):
	service = ReportService(db)
	_ensure_claim_access(service, claim_id, current_user)
	try:
		report = service.generate_for_claim(claim_id)
	except ValueError as exc:
		raise HTTPException(status_code=404, detail=str(exc)) from exc
	return GenerateReportResponse(report_id=report.id, claim_id=report.claim_id, pdf_path=report.pdf_path)


@router.get("", response_model=list[ReportResponse])
def list_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	service = ReportService(db)
	reports = service.list_reports(owner_user_id=None if current_user.role == "admin" else current_user.id)
	return [ReportResponse.model_validate(report) for report in reports]


@router.get("/{report_id}")
def download_report(
	report_id: int,
	format: Literal["pdf"] = Query(default="pdf"),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	service = ReportService(db)
	report = _ensure_report_access(service, report_id, current_user)
	if format != "pdf":
		raise HTTPException(status_code=400, detail="Only PDF format is supported for this endpoint")
	pdf_file = Path(report.pdf_path)
	if not pdf_file.exists():
		raise HTTPException(status_code=404, detail="Report file missing")
	return FileResponse(str(pdf_file), media_type="application/pdf", filename=pdf_file.name)


@router.get("/claim/{claim_id}", response_model=ReportResponse)
def latest_report_for_claim(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	service = ReportService(db)
	_ensure_claim_access(service, claim_id, current_user)
	report = service.latest_for_claim(claim_id)
	if report is None:
		raise HTTPException(status_code=404, detail="No report available for claim")
	return ReportResponse.model_validate(report)

