"""Support Vector Machine model for insurance fraud detection."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.svm import SVC

from .base_model import BaseFraudModel

LOGGER = logging.getLogger(__name__)


class SVMFraudModel(BaseFraudModel):
	"""SVM-based fraud detector with probability calibration."""

	def __init__(self) -> None:
		super().__init__(model_name="svm")
		self.model = SVC(
			kernel="rbf",
			C=1.0,
			gamma="scale",
			class_weight="balanced",
			probability=True,
			random_state=42,
		)
		self.best_params_: dict[str, Any] | None = None

	def train(self, x_train: pd.DataFrame | np.ndarray, y_train: pd.Series | np.ndarray) -> None:
		"""Train SVM model with configured hyperparameters."""
		self.model.fit(x_train, y_train)
		LOGGER.info("SVM model training complete.")

	def tune_hyperparameters(
		self,
		x_train: pd.DataFrame | np.ndarray,
		y_train: pd.Series | np.ndarray,
		cv: int = 5,
	) -> dict[str, Any]:
		"""Run grid search hyperparameter tuning for SVM.

		Args:
			x_train: Training features.
			y_train: Training labels.
			cv: Number of stratified folds.

		Returns:
			Best hyperparameter configuration.
		"""
		param_grid = {
			"C": [0.5, 1.0, 2.0, 5.0],
			"kernel": ["rbf"],
			"gamma": ["scale", "auto", 0.1, 0.01],
			"class_weight": ["balanced"],
		}
		cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
		search = GridSearchCV(
			estimator=SVC(probability=True, random_state=42),
			param_grid=param_grid,
			scoring="recall",
			cv=cv_strategy,
			n_jobs=-1,
			verbose=0,
		)
		search.fit(x_train, y_train)
		self.model = search.best_estimator_
		self.best_params_ = dict(search.best_params_)
		LOGGER.info("SVM best params: %s", self.best_params_)
		return self.best_params_

	def predict(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
		"""Predict fraud classes."""
		return self.model.predict(x)

	def predict_proba(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
		"""Predict fraud probabilities."""
		return self.model.predict_proba(x)

