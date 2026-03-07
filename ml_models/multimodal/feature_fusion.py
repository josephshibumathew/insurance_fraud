"""Feature and decision fusion strategies for multimodal fraud prediction."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LOGGER = logging.getLogger(__name__)


@dataclass
class FusionSelectionResult:
	"""Best fusion strategy result."""

	strategy_name: str
	auc: float
	model: Any
	details: dict[str, Any]


def combine_structured_and_image_features(
	structured_features: np.ndarray,
	image_features: np.ndarray,
	normalize: bool = True,
) -> tuple[np.ndarray, Pipeline | None]:
	"""Concatenate structured and image features with optional normalization."""
	if structured_features.shape[0] != image_features.shape[0]:
		raise ValueError("structured_features and image_features must have same row count.")

	fused = np.hstack([structured_features, image_features])
	if not normalize:
		return fused, None

	scaler = StandardScaler()
	fused_scaled = scaler.fit_transform(fused)
	pipeline = Pipeline([("scaler", scaler)])
	return fused_scaled, pipeline


def weighted_probability_fusion(
	structured_proba: np.ndarray,
	image_proba: np.ndarray,
	alpha: float,
) -> np.ndarray:
	"""Fuse probabilities by weighted averaging."""
	if not (0.0 <= alpha <= 1.0):
		raise ValueError("alpha must be in [0, 1].")
	return alpha * structured_proba + (1.0 - alpha) * image_proba


def decision_level_voting(
	structured_proba: np.ndarray,
	image_proba: np.ndarray,
	threshold: float = 0.5,
) -> np.ndarray:
	"""Binary decision-level fusion via majority voting."""
	s_pred = (structured_proba >= threshold).astype(int)
	i_pred = (image_proba >= threshold).astype(int)
	return ((s_pred + i_pred) >= 1).astype(int)


def _image_probability_proxy(image_features: np.ndarray) -> np.ndarray:
	"""Create image-only probability proxy from key engineered features."""
	if image_features.ndim != 2:
		raise ValueError("image_features must be 2D.")
	damage_count = image_features[:, 0]
	severity_score = image_features[:, 10] if image_features.shape[1] > 10 else image_features[:, -1]
	part_count = image_features[:, 11] if image_features.shape[1] > 11 else image_features[:, -1]

	signal = 0.2 * damage_count + 0.6 * severity_score + 0.2 * part_count
	signal = (signal - signal.min()) / (signal.max() - signal.min() + 1e-8)
	return np.clip(signal, 0.0, 1.0)


def choose_optimal_fusion_strategy(
	structured_proba: np.ndarray,
	structured_features: np.ndarray,
	image_features: np.ndarray,
	y_true: np.ndarray,
	random_state: int = 42,
) -> FusionSelectionResult:
	"""Evaluate fusion strategies and select best by validation AUC.

	Strategies:
	  a) Feature concatenation + meta-classifier (logistic baseline)
	  b) Weighted average of probabilities
	  c) Decision-level fusion (voting)
	"""
	if len(structured_proba) != len(y_true):
		raise ValueError("structured_proba and y_true lengths must match.")

	image_proba = _image_probability_proxy(image_features)

	x_train_idx, x_val_idx = train_test_split(
		np.arange(len(y_true)),
		test_size=0.2,
		random_state=random_state,
		stratify=y_true,
	)

	results: list[FusionSelectionResult] = []

	fused_features, scaler_pipeline = combine_structured_and_image_features(
		structured_features=structured_features,
		image_features=image_features,
		normalize=True,
	)
	meta_model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=random_state)
	meta_model.fit(fused_features[x_train_idx], y_true[x_train_idx])
	meta_proba = meta_model.predict_proba(fused_features[x_val_idx])[:, 1]
	meta_auc = float(roc_auc_score(y_true[x_val_idx], meta_proba))
	results.append(
		FusionSelectionResult(
			strategy_name="feature_concat_meta_classifier",
			auc=meta_auc,
			model={"meta_model": meta_model, "scaler": scaler_pipeline},
			details={"validation_size": len(x_val_idx)},
		)
	)

	best_alpha = 0.5
	best_auc = -1.0
	for alpha in np.linspace(0.0, 1.0, 21):
		fused_proba = weighted_probability_fusion(
			structured_proba=structured_proba[x_val_idx],
			image_proba=image_proba[x_val_idx],
			alpha=float(alpha),
		)
		auc = float(roc_auc_score(y_true[x_val_idx], fused_proba))
		if auc > best_auc:
			best_auc = auc
			best_alpha = float(alpha)

	results.append(
		FusionSelectionResult(
			strategy_name="weighted_probability_average",
			auc=best_auc,
			model={"alpha": best_alpha},
			details={},
		)
	)

	voting_pred = decision_level_voting(
		structured_proba=structured_proba[x_val_idx],
		image_proba=image_proba[x_val_idx],
		threshold=0.5,
	)
	voting_score = 0.5 * structured_proba[x_val_idx] + 0.5 * image_proba[x_val_idx]
	voting_auc = float(roc_auc_score(y_true[x_val_idx], voting_score))
	voting_acc = float(accuracy_score(y_true[x_val_idx], voting_pred))
	results.append(
		FusionSelectionResult(
			strategy_name="decision_level_voting",
			auc=voting_auc,
			model={"threshold": 0.5},
			details={"accuracy": voting_acc},
		)
	)

	best = max(results, key=lambda item: item.auc)
	LOGGER.info("Selected fusion strategy=%s auc=%.5f", best.strategy_name, best.auc)
	return best

