"""Convenience wrappers for evaluation metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluation import compute_confusion, compute_metrics

__all__ = ["compute_confusion", "compute_metrics"]


def summarize_metrics(
	y_true: pd.Series | np.ndarray,
	y_pred: np.ndarray,
	y_proba: np.ndarray,
) -> dict[str, float | None]:
	"""Return a combined metric summary dictionary.

	Args:
		y_true: Ground truth labels.
		y_pred: Predicted labels.
		y_proba: Positive-class probability scores.

	Returns:
		Flat dictionary containing model metrics and confusion values.
	"""
	metrics = compute_metrics(y_true=y_true, y_pred=y_pred, y_proba=y_proba)
	matrix = compute_confusion(y_true=y_true, y_pred=y_pred)
	return {**metrics, **matrix}

