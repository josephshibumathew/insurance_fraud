"""Model evaluation and reporting utilities for fraud detection."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

LOGGER = logging.getLogger(__name__)


class PredictiveModel(Protocol):
    """Protocol for model interfaces used in evaluation."""

    def predict(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
        ...

    def predict_proba(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
        ...


def _safe_auc(y_true: pd.Series | np.ndarray, y_score: np.ndarray) -> float | None:
    try:
        return float(roc_auc_score(y_true, y_score))
    except ValueError:
        return None


def compute_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
) -> dict[str, float | None]:
    """Compute classification metrics for binary fraud detection.

    Args:
        y_true: Ground truth labels.
        y_pred: Predicted labels.
        y_proba: Positive-class probability scores.

    Returns:
        Dictionary of accuracy, precision, recall, f1, and auc_roc.
    """
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "auc_roc": _safe_auc(y_true, y_proba),
    }


def compute_confusion(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> dict[str, int]:
    """Compute confusion matrix summary values.

    Args:
        y_true: Ground truth labels.
        y_pred: Predicted labels.

    Returns:
        Dictionary with TN, FP, FN, TP values.
    """
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def benchmark_inference_time(
    model: PredictiveModel,
    x_test: pd.DataFrame | np.ndarray,
    runs: int = 3,
) -> float:
    """Measure average inference latency in ms per claim.

    Args:
        model: Predictive model object.
        x_test: Test features.
        runs: Number of benchmark repetitions.

    Returns:
        Average milliseconds per claim.
    """
    x_array = np.asarray(x_test)
    if len(x_array) == 0:
        raise ValueError("x_test must contain at least one row.")

    elapsed: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        _ = model.predict(x_test)
        end = time.perf_counter()
        elapsed.append((end - start) * 1000 / len(x_array))
    return float(np.mean(elapsed))


def compare_models(
    models: dict[str, PredictiveModel],
    x_test: pd.DataFrame | np.ndarray,
    y_test: pd.Series | np.ndarray,
    report_dir: str | Path,
    performance_targets: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate and compare multiple models, then export reports.

    Args:
        models: Model dictionary keyed by model name.
        x_test: Test features.
        y_test: Test labels.
        report_dir: Output directory for report files.
        performance_targets: Optional target thresholds.

    Returns:
        Evaluation report dictionary.
    """
    out_dir = Path(report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}
    for model_name, model in models.items():
        y_pred = model.predict(x_test)
        y_prob = model.predict_proba(x_test)[:, 1]

        metrics = compute_metrics(y_true=y_test, y_pred=y_pred, y_proba=y_prob)
        matrix = compute_confusion(y_true=y_test, y_pred=y_pred)
        latency_ms = benchmark_inference_time(model=model, x_test=x_test)

        model_result: dict[str, Any] = {
            "metrics": metrics,
            "confusion_matrix": matrix,
            "inference_time_ms_per_claim": latency_ms,
        }

        if performance_targets:
            model_result["target_achievement"] = {
                "accuracy": (metrics["accuracy"] or 0.0) >= performance_targets.get("accuracy", 0.0),
                "recall": (metrics["recall"] or 0.0) >= performance_targets.get("recall", 0.0),
                "inference_time": latency_ms <= performance_targets.get(
                    "inference_time_ms_per_claim", float("inf")
                ),
            }

        results[model_name] = model_result
        LOGGER.info("%s evaluation metrics: %s", model_name, metrics)

    overall = {
        "models": results,
        "best_by_recall": max(results.items(), key=lambda item: item[1]["metrics"]["recall"])[0],
        "best_by_accuracy": max(results.items(), key=lambda item: item[1]["metrics"]["accuracy"])[0],
    }

    with (out_dir / "evaluation_report.json").open("w", encoding="utf-8") as fp:
        json.dump(overall, fp, indent=2)

    rows: list[dict[str, Any]] = []
    for name, result in results.items():
        row = {"model": name, **result["metrics"], "inference_time_ms_per_claim": result["inference_time_ms_per_claim"]}
        rows.append(row)
    pd.DataFrame(rows).to_csv(out_dir / "model_comparison.csv", index=False)

    LOGGER.info("Saved evaluation reports to %s", out_dir)
    return overall
