"""Natural language explanation integration for fraud reports."""

from __future__ import annotations

import logging
from typing import Any

LOGGER = logging.getLogger(__name__)


def extract_top_contributors(
    mapped_contributions: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Return top-k features by absolute SHAP contribution."""
    sorted_rows = sorted(mapped_contributions, key=lambda row: abs(float(row.get("shap_value", 0.0))), reverse=True)
    return sorted_rows[:top_k]


def _feature_reason_sentence(feature: dict[str, Any]) -> str:
    group = str(feature.get("original_group", "feature")).replace("_", " ")
    value = float(feature.get("feature_value", 0.0))
    shap_value = float(feature.get("shap_value", 0.0))

    if shap_value >= 0:
        return f"Elevated {group} (value={value:.2f}) increased fraud risk."
    return f"Lower-risk pattern in {group} (value={value:.2f}) reduced fraud score."


def _image_consistency_sentence(yolo_output: dict[str, Any], claim_context: dict[str, Any] | None = None) -> str:
    claim_context = claim_context or {}
    claimed_accident_type = str(claim_context.get("accident_type", "")).lower()
    affected_parts = yolo_output.get("affected_parts", [])

    if claimed_accident_type and affected_parts:
        if "rear" in claimed_accident_type and any(part in {"hood", "headlight", "windshield"} for part in affected_parts):
            return "Damage detected on front-side parts appears inconsistent with claimed rear-impact accident type."
        if "front" in claimed_accident_type and any(part in {"trunk"} for part in affected_parts):
            return "Damage detected on rear parts appears inconsistent with claimed front-impact accident type."

    if affected_parts:
        return f"Detected damage affects {', '.join(sorted(set(affected_parts)))} components."
    return "No significant image-based damage evidence detected."


def generate_natural_language_explanation(
    top_features: list[dict[str, Any]],
    yolo_output: dict[str, Any],
    claim_context: dict[str, Any] | None = None,
) -> str:
    """Generate concise natural language explanation for a claim."""
    claim_context = claim_context or {}

    if not top_features:
        feature_sentence = "Model found limited structured feature evidence for fraud."
    else:
        major_positive = [row for row in top_features if float(row.get("shap_value", 0.0)) > 0][:2]
        if major_positive:
            feature_names = [str(item.get("original_group", "feature")).replace("_", " ") for item in major_positive]
            feature_sentence = f"This claim was flagged mainly due to {', '.join(feature_names)}."
        else:
            feature_sentence = _feature_reason_sentence(top_features[0])

    consistency_sentence = _image_consistency_sentence(yolo_output=yolo_output, claim_context=claim_context)
    detail_sentences = [_feature_reason_sentence(feature) for feature in top_features[:3]]

    explanation = " ".join([feature_sentence, consistency_sentence, *detail_sentences])
    return explanation.strip()


def format_explanation_for_llm(
    claim_id: str,
    fraud_probability: float,
    top_features: list[dict[str, Any]],
    yolo_output: dict[str, Any],
    claim_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Format explanation payload for downstream LLM report generation."""
    narrative = generate_natural_language_explanation(
        top_features=top_features,
        yolo_output=yolo_output,
        claim_context=claim_context,
    )

    payload = {
        "claim_id": claim_id,
        "fraud_probability": float(fraud_probability),
        "top_contributing_features": top_features,
        "image_damage_summary": {
            "severity_score": yolo_output.get("severity_score", 0.0),
            "affected_parts": yolo_output.get("affected_parts", []),
            "count_by_damage_type": yolo_output.get("count_by_damage_type", {}),
        },
        "natural_language_explanation": narrative,
    }
    LOGGER.info("Prepared explainability payload for claim_id=%s", claim_id)
    return payload
