"""Weighted ensemble model combining SVM, RF, and XGBoost."""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold

from .rf_model import RFFraudModel
from .svm_model import SVMFraudModel
from .xgboost_model import XGBFraudModel

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnsembleWeightResult:
	"""Container for weight search output."""

	weights: tuple[float, float, float]
	score: float


class WeightedEnsembleFraudModel:
	"""Weighted voting ensemble for fraud classification.

	The ensemble aggregates fraud probabilities from SVM, Random Forest, and
	XGBoost, with weights optimized by cross-validation.
	"""

	def __init__(
		self,
		svm_model: SVMFraudModel,
		rf_model: RFFraudModel,
		xgb_model: XGBFraudModel,
		weights: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3),
	) -> None:
		self.svm_model = svm_model
		self.rf_model = rf_model
		self.xgb_model = xgb_model
		self.weights = weights

	def predict_proba(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
		"""Compute weighted probability predictions.

		Args:
			x: Feature matrix.

		Returns:
			Probability matrix of shape (n_samples, 2).
		"""
		svm_prob = self.svm_model.predict_proba(x)[:, 1]
		rf_prob = self.rf_model.predict_proba(x)[:, 1]
		xgb_prob = self.xgb_model.predict_proba(x)[:, 1]

		ensemble_prob_pos = (
			self.weights[0] * svm_prob
			+ self.weights[1] * rf_prob
			+ self.weights[2] * xgb_prob
		)
		ensemble_prob_pos = np.clip(ensemble_prob_pos, 0.0, 1.0)
		ensemble_prob = np.column_stack([1 - ensemble_prob_pos, ensemble_prob_pos])
		return ensemble_prob

	def predict(self, x: pd.DataFrame | np.ndarray, threshold: float = 0.5) -> np.ndarray:
		"""Predict class labels from weighted probabilities.

		Args:
			x: Feature matrix.
			threshold: Probability threshold for class 1.

		Returns:
			Binary class predictions.
		"""
		probs = self.predict_proba(x)[:, 1]
		return (probs >= threshold).astype(int)

	def optimize_weights(
		self,
		x_val: pd.DataFrame | np.ndarray,
		y_val: pd.Series | np.ndarray,
		cv: int = 5,
		step: float = 0.1,
		objective: str = "recall",
	) -> EnsembleWeightResult:
		"""Optimize ensemble weights via cross-validated grid search.

		Args:
			x_val: Validation features used for optimization.
			y_val: Validation labels.
			cv: Number of stratified folds.
			step: Step size for candidate weights in [0, 1].
			objective: Optimization metric, one of recall|accuracy|f1|precision|hybrid.

		Returns:
			Best ensemble weight result.
		"""
		if step <= 0 or step > 1:
			raise ValueError("step must be in the interval (0, 1].")

		y_series = pd.Series(y_val).reset_index(drop=True)
		x_frame = pd.DataFrame(x_val).reset_index(drop=True)

		candidates: list[tuple[float, float, float]] = []
		ticks = np.arange(0.0, 1.0 + step, step)
		for w1, w2 in itertools.product(ticks, ticks):
			w3 = 1.0 - (w1 + w2)
			if w3 < -1e-9:
				continue
			if w3 < 0:
				w3 = 0.0
			if abs((w1 + w2 + w3) - 1.0) <= 1e-6:
				candidates.append((float(w1), float(w2), float(w3)))

		cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
		metric_funcs: dict[str, Any] = {
			"accuracy": accuracy_score,
			"precision": lambda yt, yp: precision_score(yt, yp, zero_division=0),
			"recall": lambda yt, yp: recall_score(yt, yp, zero_division=0),
			"f1": lambda yt, yp: f1_score(yt, yp, zero_division=0),
		}

		if objective not in {"accuracy", "precision", "recall", "f1", "hybrid"}:
			raise ValueError("objective must be one of accuracy|precision|recall|f1|hybrid")

		best_score = -1.0
		best_weights = self.weights

		for weights in candidates:
			fold_scores: list[float] = []
			for _, fold_idx in cv_strategy.split(x_frame, y_series):
				x_fold = x_frame.iloc[fold_idx]
				y_fold = y_series.iloc[fold_idx]
				probs = self._weighted_proba_with_weights(x_fold, weights=weights)
				preds = (probs >= 0.5).astype(int)

				if objective == "hybrid":
					acc = metric_funcs["accuracy"](y_fold, preds)
					pre = metric_funcs["precision"](y_fold, preds)
					rec = metric_funcs["recall"](y_fold, preds)
					f1 = metric_funcs["f1"](y_fold, preds)
					fold_score = float(np.mean([acc, pre, rec, f1]))
				else:
					fold_score = float(metric_funcs[objective](y_fold, preds))
				fold_scores.append(fold_score)

			candidate_score = float(np.mean(fold_scores))
			if candidate_score > best_score:
				best_score = candidate_score
				best_weights = weights

		self.weights = best_weights
		LOGGER.info("Optimized ensemble weights=%s with %s score=%.5f", best_weights, objective, best_score)
		return EnsembleWeightResult(weights=best_weights, score=best_score)

	def _weighted_proba_with_weights(
		self,
		x: pd.DataFrame | np.ndarray,
		weights: tuple[float, float, float],
	) -> np.ndarray:
		svm_prob = self.svm_model.predict_proba(x)[:, 1]
		rf_prob = self.rf_model.predict_proba(x)[:, 1]
		xgb_prob = self.xgb_model.predict_proba(x)[:, 1]
		ensemble_prob_pos = weights[0] * svm_prob + weights[1] * rf_prob + weights[2] * xgb_prob
		return np.clip(ensemble_prob_pos, 0.0, 1.0)

	def save_model(self, path: str | Path) -> None:
		"""Serialize the ensemble wrapper and constituent models."""
		output_path = Path(path)
		output_path.parent.mkdir(parents=True, exist_ok=True)
		payload = {
			"weights": self.weights,
			"svm_model": self.svm_model.model,
			"rf_model": self.rf_model.model,
			"xgb_model": self.xgb_model.model,
		}
		joblib.dump(payload, output_path)
		LOGGER.info("Saved weighted ensemble model to %s", output_path)

	@classmethod
	def load_model(cls, path: str | Path) -> "WeightedEnsembleFraudModel":
		"""Deserialize ensemble wrapper and constituent models."""
		model_path = Path(path)
		if not model_path.exists():
			raise FileNotFoundError(f"Ensemble model file not found: {model_path}")

		payload = joblib.load(model_path)
		svm = SVMFraudModel()
		rf = RFFraudModel()
		xgb = XGBFraudModel()
		svm.model = payload["svm_model"]
		rf.model = payload["rf_model"]
		xgb.model = payload["xgb_model"]
		return cls(svm_model=svm, rf_model=rf, xgb_model=xgb, weights=tuple(payload["weights"]))

