"""XGBoost model for insurance fraud detection."""

from __future__ import annotations

import logging
import importlib
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV, StratifiedKFold

from .base_model import BaseFraudModel

LOGGER = logging.getLogger(__name__)

def _get_xgb_classifier():
	try:
		module = importlib.import_module("xgboost")
		return getattr(module, "XGBClassifier")
	except Exception as exc:
		raise ImportError(
			"xgboost is required for XGBFraudModel. Install it in requirements-ml.txt."
		) from exc


class XGBFraudModel(BaseFraudModel):
	"""XGBoost-based fraud detector."""

	def __init__(self, scale_pos_weight: float = 1.0) -> None:
		super().__init__(model_name="xgboost")
		xgb_classifier = _get_xgb_classifier()
		self.model = xgb_classifier(
			n_estimators=100,
			learning_rate=0.1,
			max_depth=6,
			subsample=1.0,
			colsample_bytree=1.0,
			objective="binary:logistic",
			eval_metric="logloss",
			scale_pos_weight=scale_pos_weight,
			random_state=42,
			n_jobs=-1,
		)
		self.best_params_: dict[str, Any] | None = None

	@staticmethod
	def compute_scale_pos_weight(y: pd.Series | np.ndarray) -> float:
		"""Compute imbalance ratio for positive class weighting.

		Args:
			y: Binary label vector.

		Returns:
			Ratio of negatives to positives.

		Raises:
			ValueError: If positive class does not exist.
		"""
		series = pd.Series(y)
		positives = int((series == 1).sum())
		negatives = int((series == 0).sum())
		if positives == 0:
			raise ValueError("Cannot compute scale_pos_weight: no positive samples found.")
		return float(negatives / positives)

	def train(self, x_train: pd.DataFrame | np.ndarray, y_train: pd.Series | np.ndarray) -> None:
		"""Train XGBoost model."""
		self.model.fit(x_train, y_train)
		LOGGER.info("XGBoost model training complete.")

	def tune_hyperparameters(
		self,
		x_train: pd.DataFrame | np.ndarray,
		y_train: pd.Series | np.ndarray,
		cv: int = 5,
	) -> dict[str, Any]:
		"""Run grid search hyperparameter tuning for XGBoost.

		Args:
			x_train: Training features.
			y_train: Training labels.
			cv: Number of stratified folds.

		Returns:
			Best hyperparameter configuration.
		"""
		scale_pos_weight = self.compute_scale_pos_weight(y_train)
		param_grid = {
			"n_estimators": [100, 200],
			"learning_rate": [0.05, 0.1],
			"max_depth": [4, 6, 8],
			"subsample": [0.8, 1.0],
			"colsample_bytree": [0.8, 1.0],
		}
		cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
		search = GridSearchCV(
			estimator=_get_xgb_classifier()(
				objective="binary:logistic",
				eval_metric="logloss",
				scale_pos_weight=scale_pos_weight,
				random_state=42,
				n_jobs=-1,
			),
			param_grid=param_grid,
			scoring="recall",
			cv=cv_strategy,
			n_jobs=-1,
			verbose=0,
		)
		search.fit(x_train, y_train)
		self.model = search.best_estimator_
		self.best_params_ = dict(search.best_params_)
		LOGGER.info("XGBoost best params: %s", self.best_params_)
		return self.best_params_

	def predict(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
		"""Predict fraud classes."""
		return self.model.predict(x)

	def predict_proba(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
		"""Predict fraud probabilities."""
		return self.model.predict_proba(x)

