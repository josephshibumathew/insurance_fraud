"""Fusion model training and inference for multimodal fraud scoring."""

from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LOGGER = logging.getLogger(__name__)


def _get_xgb_classifier():
	try:
		module = importlib.import_module("xgboost")
		return getattr(module, "XGBClassifier")
	except Exception as exc:
		raise ImportError("xgboost is required for xgboost fusion model option.") from exc


@dataclass
class FusionModelArtifacts:
	"""Artifacts container for serialization and explainability."""

	model: Any
	scaler: StandardScaler
	classifier_name: str
	feature_names: list[str]


class MultiModalFusionModel:
	"""Meta-classifier fusion model for structured + image features."""

	def __init__(self, classifier_name: str = "logistic_regression") -> None:
		supported = {"logistic_regression", "random_forest", "xgboost"}
		if classifier_name not in supported:
			raise ValueError(f"Unsupported classifier_name: {classifier_name}")

		self.classifier_name = classifier_name
		self.model: Any | None = None
		self.scaler = StandardScaler()
		self.feature_names = [
			"ensemble_proba",
			"image_severity_score",
			"damage_count",
			"part_count",
		]

	def _build_model(self):
		if self.classifier_name == "logistic_regression":
			return LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
		if self.classifier_name == "random_forest":
			return RandomForestClassifier(
				n_estimators=200,
				max_depth=8,
				min_samples_split=5,
				class_weight="balanced",
				random_state=42,
				n_jobs=-1,
			)
		xgb = _get_xgb_classifier()
		return xgb(
			n_estimators=200,
			learning_rate=0.05,
			max_depth=4,
			objective="binary:logistic",
			eval_metric="logloss",
			random_state=42,
			n_jobs=-1,
		)

	@staticmethod
	def build_core_feature_matrix(
		ensemble_proba: np.ndarray,
		image_features: np.ndarray,
	) -> np.ndarray:
		"""Build required fusion input matrix.

		Input format: [ensemble_proba, image_severity_score, damage_count, part_count]
		"""
		if image_features.ndim != 2:
			raise ValueError("image_features must be a 2D array.")
		if len(ensemble_proba) != image_features.shape[0]:
			raise ValueError("ensemble_proba length must equal image_features rows.")

		damage_count = image_features[:, 0]
		severity_score = image_features[:, 10] if image_features.shape[1] > 10 else image_features[:, -1]
		part_count = image_features[:, 11] if image_features.shape[1] > 11 else image_features[:, -1]
		return np.column_stack([ensemble_proba, severity_score, damage_count, part_count])

	def train(
		self,
		ensemble_proba: np.ndarray,
		image_features: np.ndarray,
		y_true: np.ndarray,
		validation_size: float = 0.2,
	) -> dict[str, Any]:
		"""Train fusion meta-classifier and return validation performance."""
		x = self.build_core_feature_matrix(ensemble_proba=ensemble_proba, image_features=image_features)
		x_train, x_val, y_train, y_val = train_test_split(
			x,
			y_true,
			test_size=validation_size,
			random_state=42,
			stratify=y_true,
		)

		x_train_scaled = self.scaler.fit_transform(x_train)
		x_val_scaled = self.scaler.transform(x_val)

		self.model = self._build_model()
		self.model.fit(x_train_scaled, y_train)

		val_proba = self.model.predict_proba(x_val_scaled)[:, 1]
		val_auc = float(roc_auc_score(y_val, val_proba))
		LOGGER.info("Fusion model trained | classifier=%s val_auc=%.5f", self.classifier_name, val_auc)
		return {"val_auc": val_auc, "classifier": self.classifier_name}

	def predict_proba(
		self,
		ensemble_proba: np.ndarray,
		image_features: np.ndarray,
	) -> np.ndarray:
		"""Predict final fraud probabilities."""
		if self.model is None:
			raise ValueError("Fusion model is not trained or loaded.")
		x = self.build_core_feature_matrix(ensemble_proba=ensemble_proba, image_features=image_features)
		x_scaled = self.scaler.transform(x)
		return self.model.predict_proba(x_scaled)[:, 1]

	def predict(
		self,
		ensemble_proba: np.ndarray,
		image_features: np.ndarray,
		threshold: float = 0.5,
	) -> np.ndarray:
		"""Predict binary fraud classes."""
		return (self.predict_proba(ensemble_proba, image_features) >= threshold).astype(int)

	def save(self, output_dir: str | Path | None = None, filename: str = "fusion_model.joblib") -> Path:
		"""Save fusion model artifacts to disk."""
		package_root = Path(__file__).resolve().parents[1]
		out_dir = Path(output_dir) if output_dir else package_root / "models" / "fusion"
		out_dir.mkdir(parents=True, exist_ok=True)

		artifact = FusionModelArtifacts(
			model=self.model,
			scaler=self.scaler,
			classifier_name=self.classifier_name,
			feature_names=self.feature_names,
		)
		model_path = out_dir / filename
		joblib.dump(artifact, model_path)

		metadata = {
			"classifier": self.classifier_name,
			"feature_names": self.feature_names,
		}
		(out_dir / "fusion_model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
		LOGGER.info("Saved fusion model to %s", model_path)
		return model_path

	@classmethod
	def load(cls, model_path: str | Path) -> "MultiModalFusionModel":
		"""Load fusion model artifact from disk."""
		path = Path(model_path)
		if not path.exists():
			raise FileNotFoundError(f"Fusion model not found: {path}")

		artifact: FusionModelArtifacts = joblib.load(path)
		instance = cls(classifier_name=artifact.classifier_name)
		instance.model = artifact.model
		instance.scaler = artifact.scaler
		instance.feature_names = artifact.feature_names
		return instance

