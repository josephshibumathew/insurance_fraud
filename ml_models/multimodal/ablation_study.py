"""Ablation study utilities for multimodal fusion performance comparison."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from .feature_fusion import weighted_probability_fusion
from .fusion_model import MultiModalFusionModel

LOGGER = logging.getLogger(__name__)


def _metric_row(y_true: np.ndarray, proba: np.ndarray, model_name: str) -> dict[str, Any]:
    pred = (proba >= 0.5).astype(int)
    return {
        "model": model_name,
        "auc": float(roc_auc_score(y_true, proba)),
        "accuracy": float(accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
    }


def run_ablation_study(
    y_true: np.ndarray,
    structured_proba: np.ndarray,
    image_features: np.ndarray,
    fusion_model: MultiModalFusionModel,
    output_dir: str | Path,
) -> pd.DataFrame:
    """Compare unimodal and multimodal fusion strategies.

    Compares:
      - Ensemble only
      - YOLO only (proxy from image features)
      - Simple fusion (average)
      - Advanced fusion (meta-classifier)
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    image_proxy = np.clip(
        0.2 * image_features[:, 0] + 0.6 * image_features[:, 10] + 0.2 * image_features[:, 11],
        0.0,
        None,
    )
    image_proxy = (image_proxy - image_proxy.min()) / (image_proxy.max() - image_proxy.min() + 1e-8)

    simple_avg = weighted_probability_fusion(
        structured_proba=structured_proba,
        image_proba=image_proxy,
        alpha=0.5,
    )
    advanced = fusion_model.predict_proba(
        ensemble_proba=structured_proba,
        image_features=image_features,
    )

    rows = [
        _metric_row(y_true, structured_proba, "ensemble_only"),
        _metric_row(y_true, image_proxy, "yolo_only"),
        _metric_row(y_true, simple_avg, "simple_fusion_average"),
        _metric_row(y_true, advanced, "advanced_fusion_meta_classifier"),
    ]
    df = pd.DataFrame(rows).sort_values("auc", ascending=False).reset_index(drop=True)

    csv_path = out_dir / "ablation_metrics.csv"
    json_path = out_dir / "ablation_metrics.json"
    df.to_csv(csv_path, index=False)
    json_path.write_text(df.to_json(orient="records", indent=2), encoding="utf-8")
    LOGGER.info("Saved ablation study outputs to %s", out_dir)
    return df
