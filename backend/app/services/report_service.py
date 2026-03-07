"""Report generation and retrieval service."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.claim import Claim
from app.models.report import Report

try:
	from ml_models.llm_module.pdf_generator import generate_pdf_report
	from ml_models.llm_module.report_generator import generate_report_text
	ML_MODELS_AVAILABLE = True
except Exception:
	ML_MODELS_AVAILABLE = False

	def generate_report_text(claim_data: dict[str, Any], score: float, damage_assessment: dict[str, Any], shap_explanations: dict[str, Any]) -> str:
		top_features = shap_explanations.get("top_contributing_features", [])
		feature_lines = "\n".join(
			f"- {item.get('feature', 'unknown')}: {item.get('shap_value', 0)}"
			for item in top_features
		) or "- No feature importance data available"

		return (
			"Executive Summary:\n"
			f"Claim {claim_data.get('claim_id')} has estimated fraud score {score:.3f}.\n\n"
			"Damage Assessment:\n"
			f"Severity score: {damage_assessment.get('severity_score', 0)}\n"
			f"Affected parts: {', '.join(damage_assessment.get('affected_parts', [])) or 'N/A'}\n\n"
			"SHAP Feature Importance:\n"
			f"{feature_lines}\n\n"
			"Recommendation:\n"
			"Route this claim for manual review if score is medium/high."
		)

	def generate_pdf_report(
		output_path: str | Path,
		claim_data: dict[str, Any],
		fraud_score: float,
		damage_assessment: dict[str, Any],
		shap_explanations: dict[str, Any],
		narrative_text: str,
		damage_image_paths: list[str] | None = None,
		logo_path: str | None = None,
	) -> Path:
		path = Path(output_path)
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(narrative_text, encoding="utf-8")
		return path


LOGGER = logging.getLogger(__name__)


class ReportService:
	def __init__(self, db: Session) -> None:
		self.db = db
		self.settings = get_settings()

	def _build_claim_payload(self, claim: Claim) -> dict:
		return {
			"claim_id": claim.id,
			"policy_number": claim.policy_number,
			"claim_amount": claim.claim_amount,
			"accident_date": str(claim.accident_date),
			"status": claim.status,
		}

	def _fallback_narrative(self, claim_data: dict, score: float, damage_assessment: dict, shap_explanations: dict) -> str:
		top_features = shap_explanations.get("top_contributing_features", [])
		feature_lines = "\n".join(
			f"- {item.get('feature', 'unknown')}: {item.get('shap_value', 0)}"
			for item in top_features
		) or "- No feature importance data available"

		return (
			"Executive Summary:\n"
			f"Claim {claim_data.get('claim_id')} has estimated fraud score {score:.3f}.\n\n"
			"Damage Assessment:\n"
			f"Severity score: {damage_assessment.get('severity_score', 0)}\n"
			f"Affected parts: {', '.join(damage_assessment.get('affected_parts', [])) or 'N/A'}\n\n"
			"SHAP Feature Importance:\n"
			f"{feature_lines}\n\n"
			"Recommendation:\n"
			"Route this claim for manual review if score is medium/high."
		)

	def generate_for_claim(self, claim_id: int) -> Report:
		if not ML_MODELS_AVAILABLE:
			LOGGER.warning("ml_models package unavailable; using report fallback mode")

		claim = self.db.get(Claim, claim_id)
		if claim is None:
			raise ValueError("Claim not found")

		claim_data = self._build_claim_payload(claim)
		damage_assessment = {
			"severity_score": 0.41,
			"affected_parts": ["front_bumper", "hood"],
			"count_by_damage_type": {"scratch": 2, "dent": 1},
			"inconsistencies": [],
		}
		shap_explanations = {
			"top_contributing_features": [
				{"feature": "claim_amount", "shap_value": 0.24},
				{"feature": "policy_pattern", "shap_value": 0.12},
				{"feature": "accident_recency", "shap_value": -0.03},
			]
		}
		score = float(claim.fraud_score or 0.25)
		try:
			narrative = generate_report_text(claim_data, score, damage_assessment, shap_explanations)
		except Exception as exc:
			LOGGER.warning("Falling back to local narrative for claim %s due to LLM error: %s", claim_id, exc)
			narrative = self._fallback_narrative(claim_data, score, damage_assessment, shap_explanations)

		reports_dir = Path(self.settings.reports_dir)
		reports_dir.mkdir(parents=True, exist_ok=True)
		pdf_path = reports_dir / f"claim_{claim.id}_{int(claim.id)}.pdf"

		generate_pdf_report(
			output_path=pdf_path,
			claim_data=claim_data,
			fraud_score=score,
			damage_assessment=damage_assessment,
			shap_explanations=shap_explanations,
			narrative_text=narrative,
		)

		report = Report(claim_id=claim.id, pdf_path=str(pdf_path))
		self.db.add(report)
		self.db.commit()
		self.db.refresh(report)
		return report

	def get_report(self, report_id: int) -> Report | None:
		return self.db.get(Report, report_id)

	def latest_for_claim(self, claim_id: int) -> Report | None:
		stmt = select(Report).where(Report.claim_id == claim_id).order_by(Report.created_at.desc()).limit(1)
		return self.db.execute(stmt).scalar_one_or_none()

	def list_reports(self, owner_user_id: int | None = None) -> list[Report]:
		stmt = select(Report).join(Claim, Claim.id == Report.claim_id)
		if owner_user_id is not None:
			stmt = stmt.where(Claim.user_id == owner_user_id)
		stmt = stmt.order_by(Report.created_at.desc())
		return list(self.db.execute(stmt).scalars().all())

