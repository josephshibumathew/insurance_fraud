"""Report schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: int
    claim_id: int
    pdf_path: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateReportResponse(BaseModel):
    report_id: int
    claim_id: int
    pdf_path: str
