"""Prompt templates for fraud decision report generation."""

from __future__ import annotations

from dataclasses import dataclass


SYSTEM_PROMPT = """
You are an insurance fraud analysis assistant writing professional, factual reports.
Rules:
1) Use ONLY facts provided in input context.
2) Do not invent policy details, evidence, timelines, or claimant statements.
3) Use concise, neutral, professional language.
4) Include sections exactly: Executive Summary, Evidence Review, SHAP Insights, Recommendation, Next Steps, Disclaimer.
5) If evidence is missing, explicitly state "Insufficient evidence provided".
6) Do not include personal identifying information in output.
7) Avoid offensive, discriminatory, or inappropriate content.
""".strip()


@dataclass(frozen=True)
class PromptTemplate:
	risk_label: str
	template: str


LOW_RISK_TEMPLATE = PromptTemplate(
	risk_label="low",
	template="""
Claim ID: {claim_id}
Fraud Score: {fraud_score:.3f}
Risk Level: LOW

Claim Details:
{claim_details}

Damage Assessment:
{damage_summary}

SHAP Explanation Summary:
{shap_summary}

Instructions:
- Summarize claim details.
- State that no strong fraud indicators were found.
- Suggest fast-track approval with routine post-approval audit.
""".strip(),
)


MEDIUM_RISK_TEMPLATE = PromptTemplate(
	risk_label="medium",
	template="""
Claim ID: {claim_id}
Fraud Score: {fraud_score:.3f}
Risk Level: MEDIUM

Claim Details:
{claim_details}

Damage Assessment:
{damage_summary}

SHAP Explanation Summary:
{shap_summary}

Instructions:
- Highlight suspicious patterns and uncertainty points.
- List damage inconsistencies between textual claim and image analysis.
- Recommend manual review before payout.
""".strip(),
)


HIGH_RISK_TEMPLATE = PromptTemplate(
	risk_label="high",
	template="""
Claim ID: {claim_id}
Fraud Score: {fraud_score:.3f}
Risk Level: HIGH

Claim Details:
{claim_details}

Damage Assessment:
{damage_summary}

SHAP Explanation Summary:
{shap_summary}

Instructions:
- Detail primary fraud indicators from structured and image signals.
- Explicitly reference highest SHAP feature contributions.
- Recommend denial with concise, evidence-based reasons.
""".strip(),
)


REJECTED_TEMPLATE = PromptTemplate(
	risk_label="rejected",
	template="""
Claim ID: {claim_id}
Fraud Score: {fraud_score:.3f}
Decision Context: CLAIM REJECTED

Claim Details:
{claim_details}

Damage Assessment:
{damage_summary}

SHAP Explanation Summary:
{shap_summary}

Policy Violations:
{policy_violations}

Instructions:
- Explain the rejection decision using direct evidence.
- Reference specific policy violations from provided context.
- Keep rationale legally cautious and professional.
""".strip(),
)


def select_template(fraud_score: float, rejected: bool = False) -> PromptTemplate:
	"""Select risk-template by fraud score bands."""
	if rejected:
		return REJECTED_TEMPLATE
	if fraud_score < 0.35:
		return LOW_RISK_TEMPLATE
	if fraud_score < 0.70:
		return MEDIUM_RISK_TEMPLATE
	return HIGH_RISK_TEMPLATE

