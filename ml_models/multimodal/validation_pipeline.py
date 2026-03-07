"""Validation pipeline for end-to-end multimodal fusion."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import roc_auc_score

from .ablation_study import run_ablation_study
from .fusion_model import MultiModalFusionModel

LOGGER = logging.getLogger(__name__)


def validate_fusion_improvement(
    y_true: np.ndarray,
    structured_proba: np.ndarray,
    image_features: np.ndarray,
    fusion_model: MultiModalFusionModel,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Validate multimodal fusion against unimodal baselines.

    Checks:
      - AUC uplift >= 5% over best single modality
      - Fusion-only processing time < 50ms/claim
      - Logs fusion coefficients/importances for interpretability
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    fusion_proba = fusion_model.predict_proba(ensemble_proba=structured_proba, image_features=image_features)
    elapsed_ms = (time.perf_counter() - start) * 1000
    per_claim_ms = elapsed_ms / max(1, len(y_true))

    image_proxy = np.clip(
        0.2 * image_features[:, 0] + 0.6 * image_features[:, 10] + 0.2 * image_features[:, 11],
        0.0,
        None,
    )
    image_proxy = (image_proxy - image_proxy.min()) / (image_proxy.max() - image_proxy.min() + 1e-8)

    auc_struct = float(roc_auc_score(y_true, structured_proba))
    auc_image = float(roc_auc_score(y_true, image_proxy))
    auc_fusion = float(roc_auc_score(y_true, fusion_proba))

    best_single = max(auc_struct, auc_image)
    uplift_pct = ((auc_fusion - best_single) / max(1e-8, best_single)) * 100.0

    interpretability: dict[str, Any] = {
        "classifier": fusion_model.classifier_name,
        "feature_names": fusion_model.feature_names,
    }
    estimator = fusion_model.model
    if estimator is not None and hasattr(estimator, "coef_"):
        interpretability["coefficients"] = estimator.coef_.tolist()
    if estimator is not None and hasattr(estimator, "feature_importances_"):
        interpretability["feature_importances"] = estimator.feature_importances_.tolist()

    ablation_df = run_ablation_study(
        y_true=y_true,
        structured_proba=structured_proba,
        image_features=image_features,
        fusion_model=fusion_model,
        output_dir=out_dir / "ablation",
    )

    result = {
        "auc": {
            "structured_only": auc_struct,
            "image_only": auc_image,
            "fusion": auc_fusion,
            "uplift_percent": uplift_pct,
            "meets_target_5_percent": bool(uplift_pct >= 5.0),
        },
        "latency": {
            "fusion_ms_per_claim": per_claim_ms,
            "meets_target_50ms": bool(per_claim_ms < 50.0),
        },
        "interpretability": interpretability,
        "ablation_top_model": ablation_df.iloc[0].to_dict() if not ablation_df.empty else None,
    }

    report_path = out_dir / "validation_report.json"
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    LOGGER.info("Saved validation report to %s", report_path)
    return result
