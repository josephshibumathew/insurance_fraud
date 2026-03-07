from __future__ import annotations

from pathlib import Path

import pytest

from ml_models.llm_module.pdf_generator import generate_pdf_report


def test_pdf_generation_creates_file(tmp_path):
    output = tmp_path / "report.pdf"

    try:
        generated = generate_pdf_report(
            output_path=output,
            claim_data={"claim_id": 1, "policy_number": "P-1", "claim_amount": 1000},
            fraud_score=0.6,
            damage_assessment={"severity_score": 0.4, "affected_parts": ["bumper"], "count_by_damage_type": {"scratch": 1}},
            shap_explanations={"top_contributing_features": [{"feature": "claim_amount", "shap_value": 0.2}]},
            narrative_text="Recommendation:\n- Manual review",
        )
    except ImportError:
        pytest.skip("reportlab not installed in environment")

    assert Path(generated).exists()
    assert Path(generated).stat().st_size > 0
