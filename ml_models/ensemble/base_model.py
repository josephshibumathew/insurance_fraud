"""Abstract base class for fraud detection models."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


class BaseFraudModel(ABC):
	"""Base abstraction for all fraud detection models.

	Subclasses must implement training and inference interfaces while keeping
	artifacts serializable for deployment.
	"""

	def __init__(self, model_name: str) -> None:
		self.model_name = model_name
		self.model: Any = None

	@abstractmethod
	def train(self, x_train: pd.DataFrame | np.ndarray, y_train: pd.Series | np.ndarray) -> None:
		"""Train the model.

		Args:
			x_train: Feature matrix.
			y_train: Label vector.
		"""

	@abstractmethod
	def predict(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
		"""Predict class labels.

		Args:
			x: Feature matrix.

		Returns:
			Predicted class labels.
		"""

	@abstractmethod
	def predict_proba(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
		"""Predict class probabilities.

		Args:
			x: Feature matrix.

		Returns:
			Probability matrix with shape (n_samples, 2).
		"""

	def save_model(self, path: str | Path) -> None:
		"""Persist model artifact to disk.

		Args:
			path: Output model file path.

		Raises:
			ValueError: If model is not trained.
		"""
		if self.model is None:
			raise ValueError(f"Model '{self.model_name}' has not been trained.")
		output_path = Path(path)
		output_path.parent.mkdir(parents=True, exist_ok=True)
		joblib.dump(self.model, output_path)
		LOGGER.info("Saved %s model to %s", self.model_name, output_path)

	def load_model(self, path: str | Path) -> None:
		"""Load model artifact from disk.

		Args:
			path: Serialized model path.

		Raises:
			FileNotFoundError: If path does not exist.
		"""
		model_path = Path(path)
		if not model_path.exists():
			raise FileNotFoundError(f"Model file does not exist: {model_path}")
		self.model = joblib.load(model_path)
		LOGGER.info("Loaded %s model from %s", self.model_name, model_path)

