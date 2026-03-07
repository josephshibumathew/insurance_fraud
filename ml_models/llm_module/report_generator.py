"""LLM-driven fraud report text generation and validation."""

from __future__ import annotations

import json
import re
from typing import Any

from .groq_client import GroqClient, build_groq_client
from .prompt_templates import SYSTEM_PROMPT, select_template
from .response_parser import format_for_consistent_display, parse_report_sections


DISALLOWED_RESPONSE_PATTERNS = [
	re.compile(r"\bkill\b", re.IGNORECASE),
	re.compile(r"\bterror\b", re.IGNORECASE),
	re.compile(r"\bnazi\b", re.IGNORECASE),
]

REQUIRED_SECTIONS = {
	"Executive Summary",
	"Evidence Review",
	"SHAP Insights",
	"Recommendation",
	"Next Steps",
	"Disclaimer",
}

PII_KEYS = {
	"first_name",
	"last_name",
	"full_name",
	"email",
	"phone",
	"address",
	"ssn",
	"national_id",
	"license_number",
	"dob",
	"date_of_birth",
}


def _redact_pii(obj: Any) -> Any:
	if isinstance(obj, dict):
		sanitized: dict[str, Any] = {}
		for key, value in obj.items():
			if key.lower() in PII_KEYS:
				sanitized[key] = "[REDACTED]"
			else:
				sanitized[key] = _redact_pii(value)
		return sanitized
	if isinstance(obj, list):
		return [_redact_pii(item) for item in obj]
	if isinstance(obj, str):
		value = re.sub(r"\b[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", obj)
		value = re.sub(r"\b\+?[0-9][0-9\-\s()]{7,}[0-9]\b", "[REDACTED_PHONE]", value)
		return value
	return obj


def _summarize_damage_assessment(damage_assessment: dict[str, Any]) -> str:
	severity = damage_assessment.get("severity_score", 0.0)
	affected = damage_assessment.get("affected_parts", [])
	counts = damage_assessment.get("count_by_damage_type", {})
	inconsistencies = damage_assessment.get("inconsistencies", [])
	return (
		f"Severity score: {float(severity):.3f}; "
		f"Affected parts: {', '.join(map(str, affected)) if affected else 'none'}; "
		f"Damage counts: {counts if counts else 'none'}; "
		f"Inconsistencies: {inconsistencies if inconsistencies else 'none'}"
	)


def _summarize_shap(shap_explanations: dict[str, Any]) -> str:
	top_features = shap_explanations.get("top_contributing_features") or shap_explanations.get("top_features") or []
	if not top_features:
		return "Insufficient SHAP detail provided."
	top_lines: list[str] = []
	for row in top_features[:8]:
		feature = row.get("feature") or row.get("original_group") or "unknown_feature"
		value = row.get("shap_value", row.get("value", 0.0))
		top_lines.append(f"- {feature}: {float(value):.4f}")
	return "\n".join(top_lines)


def _build_user_prompt(
	claim_data: dict[str, Any],
	fraud_score: float,
	damage_assessment: dict[str, Any],
	shap_explanations: dict[str, Any],
) -> str:
	rejected = bool(claim_data.get("is_rejected", False) or claim_data.get("status") == "rejected")
	template = select_template(fraud_score, rejected=rejected)

	claim_id = str(claim_data.get("claim_id") or claim_data.get("id") or "unknown")
	policy_violations = claim_data.get("policy_violations") or []
	policy_violations_text = "\n".join(f"- {item}" for item in policy_violations) if policy_violations else "None listed"

	claim_details_text = json.dumps(claim_data, indent=2, default=str)
	return template.template.format(
		claim_id=claim_id,
		fraud_score=float(fraud_score),
		claim_details=claim_details_text,
		damage_summary=_summarize_damage_assessment(damage_assessment),
		shap_summary=_summarize_shap(shap_explanations),
		policy_violations=policy_violations_text,
	)


def _content_filter(text: str) -> str:
	for pattern in DISALLOWED_RESPONSE_PATTERNS:
		if pattern.search(text):
			raise ValueError("LLM response failed content safety filter.")
	return text


def generate_report_text(
	claim_data: dict[str, Any],
	fraud_score: float,
	damage_assessment: dict[str, Any],
	shap_explanations: dict[str, Any],
	client: GroqClient | None = None,
	model: str | None = None,
) -> str:
	"""Generate professional narrative report text using Groq."""
	sanitized_claim = _redact_pii(claim_data)
	sanitized_damage = _redact_pii(damage_assessment)
	sanitized_shap = _redact_pii(shap_explanations)

	user_prompt = _build_user_prompt(
		claim_data=sanitized_claim,
		fraud_score=fraud_score,
		damage_assessment=sanitized_damage,
		shap_explanations=sanitized_shap,
	)

	llm_client = client or build_groq_client(model=model or "llama3-70b-8192")
	raw_response = llm_client.generate(
		system_prompt=SYSTEM_PROMPT,
		user_prompt=user_prompt,
		model=model,
		temperature=0.15,
		max_tokens=1400,
	)

	filtered = _content_filter(raw_response)
	formatted = format_for_consistent_display(filtered)
	if "AI-generated and should be reviewed by a qualified insurance professional" not in formatted:
		formatted += (
			"\n\nDisclaimer:\n"
			"This report is AI-generated and should be reviewed by a qualified insurance professional"
		)
	return formatted


def validate_report(report_text: str) -> bool:
	"""Validate section coverage, tone, and hallucination heuristics."""
	if not isinstance(report_text, str) or len(report_text.strip()) < 120:
		return False

	sections = parse_report_sections(report_text)
	if not REQUIRED_SECTIONS.issubset(set(sections.keys())):
		return False

	lower = report_text.lower()
	hallucination_flags = [
		"as confirmed by police transcript" in lower,
		"witness interview attached" in lower,
		"bank statement confirms" in lower,
	]
	if any(hallucination_flags):
		return False

	unprofessional_markers = ["lol", "omg", "totally", "kinda", "crazy"]
	if any(marker in lower for marker in unprofessional_markers):
		return False

	try:
		_content_filter(report_text)
	except Exception:
		return False

	return True

