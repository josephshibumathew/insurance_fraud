"""Random Forest model for insurance fraud detection."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold

from .base_model import BaseFraudModel

LOGGER = logging.getLogger(__name__)


class RFFraudModel(BaseFraudModel):
	"""Random Forest-based fraud detector."""

	def __init__(self) -> None:
		super().__init__(model_name="random_forest")
		self.model = RandomForestClassifier(
			n_estimators=100,
			max_depth=10,
			min_samples_split=5,
			class_weight="balanced",
			random_state=42,
			n_jobs=-1,
		)
		self.best_params_: dict[str, Any] | None = None

	def train(self, x_train: pd.DataFrame | np.ndarray, y_train: pd.Series | np.ndarray) -> None:
		"""Train RF model with configured hyperparameters."""
		self.model.fit(x_train, y_train)
		LOGGER.info("Random Forest model training complete.")

	def tune_hyperparameters(
		self,
		x_train: pd.DataFrame | np.ndarray,
		y_train: pd.Series | np.ndarray,
		cv: int = 5,
	) -> dict[str, Any]:
		"""Run grid search hyperparameter tuning for RF.

		Args:
			x_train: Training features.
			y_train: Training labels.
			cv: Number of stratified folds.

		Returns:
			Best hyperparameter configuration.
		"""
		param_grid = {
			"n_estimators": [100, 200, 300],
			"max_depth": [8, 10, 12, None],
			"min_samples_split": [2, 5, 10],
			"min_samples_leaf": [1, 2, 4],
		}
		cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
		search = GridSearchCV(
			estimator=RandomForestClassifier(
				class_weight="balanced",
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
		LOGGER.info("Random Forest best params: %s", self.best_params_)
		return self.best_params_

	def get_feature_importance(self, feature_names: list[str]) -> pd.DataFrame:
		"""Return sorted feature importance dataframe.

		Args:
			feature_names: Feature names aligned to model input columns.

		Returns:
			Dataframe of feature importances sorted descending.

		Raises:
			ValueError: If model is not trained yet.
		"""
		if not hasattr(self.model, "feature_importances_"):
			raise ValueError("Feature importances unavailable. Train model first.")
		importance = pd.DataFrame(
			{
				"feature": feature_names,
				"importance": self.model.feature_importances_,
			}
		).sort_values("importance", ascending=False)
		return importance.reset_index(drop=True)

	def predict(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
		"""Predict fraud classes."""
		return self.model.predict(x)

	def predict_proba(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
		"""Predict fraud probabilities."""
		return self.model.predict_proba(x)

