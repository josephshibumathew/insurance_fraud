"""SHAP explainability engine for fraud detection models."""

from __future__ import annotations

import importlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd

from .feature_mapper import FeatureMapper

LOGGER = logging.getLogger(__name__)


def _load_shap_module():
	try:
		return importlib.import_module("shap")
	except Exception as exc:
		raise ImportError("shap is required for explainability. Install with `pip install shap`.") from exc


@dataclass
class LocalExplanation:
	"""Container for local SHAP explanation."""

	shap_values: np.ndarray
	base_value: float
	prediction: float
	feature_values: dict[str, float]
	mapped_feature_contributions: list[dict[str, Any]]
	elapsed_seconds: float


@dataclass
class GlobalExplanation:
	"""Container for global SHAP explanation summary."""

	shap_values: np.ndarray
	feature_importance: pd.DataFrame
	elapsed_seconds: float


class ShapExplainerEngine:
	"""SHAP wrapper for multiple model types.

	Supports:
	  - TreeExplainer for tree-based models (RF/XGBoost)
	  - KernelExplainer for non-tree models (e.g., SVM)
	"""

	def __init__(
		self,
		model: Any,
		model_type: str,
		feature_names: list[str],
		background_data: np.ndarray | pd.DataFrame,
		predict_proba_fn: Callable[[np.ndarray], np.ndarray] | None = None,
		feature_mapper: FeatureMapper | None = None,
	) -> None:
		self.model = model
		self.model_type = model_type.lower()
		self.feature_names = feature_names
		self.background_data = (
			background_data.values if isinstance(background_data, pd.DataFrame) else np.asarray(background_data)
		)
		self.predict_proba_fn = predict_proba_fn
		self.feature_mapper = feature_mapper or FeatureMapper(feature_names=feature_names)

		if self.background_data.ndim != 2:
			raise ValueError("background_data must be 2D.")

		self._shap = _load_shap_module()
		self._explainer = self._init_explainer()

	def _init_explainer(self):
		if self.model_type in {"random_forest", "rf", "xgboost", "xgb", "tree"}:
			return self._shap.TreeExplainer(self.model)

		if self.predict_proba_fn is None:
			if hasattr(self.model, "predict_proba"):
				self.predict_proba_fn = lambda x: self.model.predict_proba(x)[:, 1]
			else:
				self.predict_proba_fn = lambda x: self.model.predict(x)

		background = self.background_data
		if len(background) > 100:
			sample_idx = np.random.RandomState(42).choice(len(background), size=100, replace=False)
			background = background[sample_idx]

		return self._shap.KernelExplainer(self.predict_proba_fn, background)

	def _extract_shap_values(self, shap_output: Any) -> np.ndarray:
		if hasattr(shap_output, "values"):
			values = shap_output.values
			if isinstance(values, list):
				return np.asarray(values[-1])
			arr = np.asarray(values)
			if arr.ndim == 3:
				return arr[:, :, -1]
			return arr

		if isinstance(shap_output, list):
			return np.asarray(shap_output[-1])
		arr = np.asarray(shap_output)
		if arr.ndim == 3:
			return arr[:, :, -1]
		return arr

	def explain_local(self, x_row: np.ndarray | pd.DataFrame, prediction: float | None = None) -> LocalExplanation:
		"""Generate local SHAP explanation for a single prediction."""
		start = time.perf_counter()
		x = x_row.values if isinstance(x_row, pd.DataFrame) else np.asarray(x_row)
		if x.ndim == 1:
			x = x.reshape(1, -1)
		if x.shape[0] != 1:
			raise ValueError("explain_local expects exactly one sample.")

		shap_values_raw = self._explainer.shap_values(x)
		shap_values = self._extract_shap_values(shap_values_raw).reshape(-1)

		if hasattr(self._explainer, "expected_value"):
			expected = self._explainer.expected_value
			if isinstance(expected, (list, tuple, np.ndarray)):
				base_value = float(np.asarray(expected).reshape(-1)[-1])
			else:
				base_value = float(expected)
		else:
			base_value = 0.0

		if prediction is None:
			if self.predict_proba_fn:
				prediction = float(self.predict_proba_fn(x)[0])
			elif hasattr(self.model, "predict_proba"):
				prediction = float(self.model.predict_proba(x)[:, 1][0])
			else:
				prediction = float(self.model.predict(x)[0])

		feature_values = {name: float(value) for name, value in zip(self.feature_names, x.reshape(-1))}
		mapped = self.feature_mapper.map_contributions(
			feature_names=self.feature_names,
			shap_values=shap_values,
			feature_values=x.reshape(-1),
		)

		elapsed = time.perf_counter() - start
		return LocalExplanation(
			shap_values=shap_values,
			base_value=base_value,
			prediction=float(prediction),
			feature_values=feature_values,
			mapped_feature_contributions=mapped,
			elapsed_seconds=elapsed,
		)

	def explain_global(self, x_data: np.ndarray | pd.DataFrame, max_samples: int = 500) -> GlobalExplanation:
		"""Generate global SHAP explanation for a dataset sample."""
		start = time.perf_counter()
		x = x_data.values if isinstance(x_data, pd.DataFrame) else np.asarray(x_data)
		if x.ndim != 2:
			raise ValueError("x_data must be 2D.")

		if len(x) > max_samples:
			sample_idx = np.random.RandomState(42).choice(len(x), size=max_samples, replace=False)
			x = x[sample_idx]

		shap_values_raw = self._explainer.shap_values(x)
		shap_values = self._extract_shap_values(shap_values_raw)

		abs_mean = np.mean(np.abs(shap_values), axis=0)
		importance = pd.DataFrame(
			{
				"feature": self.feature_names,
				"mean_abs_shap": abs_mean,
			}
		).sort_values("mean_abs_shap", ascending=False)

		elapsed = time.perf_counter() - start
		LOGGER.info("Generated global SHAP explanation in %.3fs", elapsed)
		return GlobalExplanation(
			shap_values=shap_values,
			feature_importance=importance.reset_index(drop=True),
			elapsed_seconds=elapsed,
		)

