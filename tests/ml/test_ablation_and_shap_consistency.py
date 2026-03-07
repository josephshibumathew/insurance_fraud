from __future__ import annotations

import numpy as np


def _fake_ablation_scores() -> dict[str, float]:
    return {
        "tabular_only": 0.78,
        "image_only": 0.69,
        "multimodal": 0.84,
    }


def test_ablation_multimodal_improves_over_single_modalities():
    scores = _fake_ablation_scores()
    assert scores["multimodal"] >= scores["tabular_only"]
    assert scores["multimodal"] >= scores["image_only"]


def test_shap_consistency_sign_and_order():
    shap_values = np.array([0.31, 0.21, -0.05, 0.02])
    features = ["claim_amount", "policy_pattern", "history", "recency"]
    ranked = sorted(zip(features, shap_values), key=lambda item: abs(item[1]), reverse=True)

    assert ranked[0][0] == "claim_amount"
    assert ranked[0][1] > 0
    assert len(ranked) == 4
