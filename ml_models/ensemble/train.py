"""Training pipeline for weighted ensemble fraud detection."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score

from ml_models.data.imbalance import random_undersample_train
from ml_models.evaluation.evaluation import compare_models

from .model_optimization import optimize_models_for_recall
from .rf_model import RFFraudModel
from .svm_model import SVMFraudModel
from .weighted_ensemble import WeightedEnsembleFraudModel
from .xgboost_model import XGBFraudModel

LOGGER = logging.getLogger(__name__)


def _configure_logging() -> None:
	if not logging.getLogger().handlers:
		logging.basicConfig(
			level=logging.INFO,
			format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
		)


def _load_split(path: Path, target_column: str) -> tuple[pd.DataFrame, pd.Series]:
	if not path.exists():
		raise FileNotFoundError(f"Split file not found: {path}")
	df = pd.read_csv(path)
	if target_column not in df.columns:
		raise ValueError(f"Target column '{target_column}' missing in {path}")
	x = df.drop(columns=[target_column])
	y = df[target_column]
	return x, y


def load_preprocessed_splits(
	data_root: str | Path,
	target_column: str = "fraud_label",
) -> dict[str, Any]:
	"""Load preprocessed train/val/test splits from disk.

	Args:
		data_root: Directory containing split CSV files.
		target_column: Target label name.

	Returns:
		Dictionary with split feature and label data.
	"""
	root = Path(data_root)
	train_x, train_y = _load_split(root / "train" / "train_processed.csv", target_column)
	val_x, val_y = _load_split(root / "val" / "val_processed.csv", target_column)
	test_x, test_y = _load_split(root / "test" / "test_processed.csv", target_column)

	return {
		"X_train": train_x,
		"y_train": train_y,
		"X_val": val_x,
		"y_val": val_y,
		"X_test": test_x,
		"y_test": test_y,
	}


def _cross_validate_model(
	estimator,
	x: pd.DataFrame,
	y: pd.Series,
	cv: int = 5,
) -> dict[str, float]:
	cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
	metrics = {
		"accuracy": cross_val_score(estimator, x, y, cv=cv_strategy, scoring="accuracy", n_jobs=-1),
		"precision": cross_val_score(estimator, x, y, cv=cv_strategy, scoring="precision", n_jobs=-1),
		"recall": cross_val_score(estimator, x, y, cv=cv_strategy, scoring="recall", n_jobs=-1),
		"f1": cross_val_score(estimator, x, y, cv=cv_strategy, scoring="f1", n_jobs=-1),
	}
	return {f"cv_{k}": float(np.mean(v)) for k, v in metrics.items()}


def train_ensemble_engine(
	data_root: str | Path | None = None,
	model_root: str | Path | None = None,
	report_root: str | Path | None = None,
	target_column: str = "fraud_label",
	apply_rus: bool = True,
	tune_models: bool = True,
	cv_folds: int = 5,
) -> dict[str, Any]:
	"""Train individual models and weighted ensemble.

	Args:
		data_root: Directory containing preprocessed train/val/test splits.
		model_root: Root path to save trained model artifacts.
		report_root: Root path to save evaluation reports.
		target_column: Target label column.
		apply_rus: Whether to apply random undersampling on training split.
		tune_models: Whether to run hyperparameter optimization.
		cv_folds: Number of cross-validation folds.

	Returns:
		Training and evaluation summary payload.
	"""
	_configure_logging()
	package_root = Path(__file__).resolve().parents[1]
	resolved_data_root = Path(data_root) if data_root else package_root / "data"
	resolved_model_root = Path(model_root) if model_root else package_root / "models" / "ensemble"
	resolved_report_root = Path(report_root) if report_root else package_root / "evaluation" / "reports"

	resolved_model_root.mkdir(parents=True, exist_ok=True)
	individual_dir = resolved_model_root / "individual"
	individual_dir.mkdir(parents=True, exist_ok=True)
	resolved_report_root.mkdir(parents=True, exist_ok=True)

	splits = load_preprocessed_splits(resolved_data_root, target_column=target_column)
	x_train, y_train = splits["X_train"], splits["y_train"]
	x_val, y_val = splits["X_val"], splits["y_val"]
	x_test, y_test = splits["X_test"], splits["y_test"]

	scale_pos_weight = XGBFraudModel.compute_scale_pos_weight(y_train)
	LOGGER.info("Computed XGBoost scale_pos_weight: %.5f", scale_pos_weight)

	if apply_rus:
		x_train_fit, y_train_fit, sampling_stats = random_undersample_train(x_train, y_train)
		LOGGER.info("RUS stats: %s", sampling_stats)
	else:
		x_train_fit, y_train_fit = x_train, y_train
		sampling_stats = None

	svm_model = SVMFraudModel()
	rf_model = RFFraudModel()
	xgb_model = XGBFraudModel(scale_pos_weight=scale_pos_weight)

	if tune_models:
		LOGGER.info("Starting recall-focused model optimization.")
		best_params = optimize_models_for_recall(
			svm_model=svm_model,
			rf_model=rf_model,
			xgb_model=xgb_model,
			x_train=x_train_fit,
			y_train=y_train_fit,
			cv=cv_folds,
		)
	else:
		best_params = {}

	cv_metrics = {
		"svm": _cross_validate_model(svm_model.model, x_train_fit, y_train_fit, cv=cv_folds),
		"random_forest": _cross_validate_model(rf_model.model, x_train_fit, y_train_fit, cv=cv_folds),
		"xgboost": _cross_validate_model(xgb_model.model, x_train_fit, y_train_fit, cv=cv_folds),
	}

	svm_model.train(x_train_fit, y_train_fit)
	rf_model.train(x_train_fit, y_train_fit)
	xgb_model.train(x_train_fit, y_train_fit)

	svm_model.save_model(individual_dir / "svm_model.joblib")
	rf_model.save_model(individual_dir / "rf_model.joblib")
	xgb_model.save_model(individual_dir / "xgb_model.joblib")

	ensemble = WeightedEnsembleFraudModel(
		svm_model=svm_model,
		rf_model=rf_model,
		xgb_model=xgb_model,
	)
	weight_result = ensemble.optimize_weights(
		x_val=x_val,
		y_val=y_val,
		cv=cv_folds,
		step=0.1,
		objective="recall",
	)
	ensemble_path = resolved_model_root / "ensemble.pkl"
	ensemble.save_model(ensemble_path)

	model_registry = {
		"svm": svm_model,
		"random_forest": rf_model,
		"xgboost": xgb_model,
		"weighted_ensemble": ensemble,
	}

	evaluation = compare_models(
		models=model_registry,
		x_test=x_test,
		y_test=y_test,
		report_dir=resolved_report_root,
		performance_targets={
			"accuracy": 0.9994,
			"recall": 1.0,
			"inference_time_ms_per_claim": 200.0,
		},
	)

	training_summary = {
		"best_params": best_params,
		"cv_metrics": cv_metrics,
		"optimized_weights": {
			"weights": weight_result.weights,
			"score": weight_result.score,
		},
		"sampling_stats": None if sampling_stats is None else sampling_stats.__dict__,
		"evaluation": evaluation,
		"artifacts": {
			"svm": str(individual_dir / "svm_model.joblib"),
			"random_forest": str(individual_dir / "rf_model.joblib"),
			"xgboost": str(individual_dir / "xgb_model.joblib"),
			"ensemble": str(ensemble_path),
		},
	}

	with (resolved_report_root / "training_summary.json").open("w", encoding="utf-8") as fp:
		json.dump(training_summary, fp, indent=2)
	LOGGER.info("Training summary saved to %s", resolved_report_root / "training_summary.json")
	return training_summary


if __name__ == "__main__":
	train_ensemble_engine()

