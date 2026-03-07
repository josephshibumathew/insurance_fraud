"""Hyperparameter optimization utilities for fraud models."""

from __future__ import annotations

import logging
import importlib
from typing import Any

import pandas as pd

from .rf_model import RFFraudModel
from .svm_model import SVMFraudModel
from .xgboost_model import XGBFraudModel

LOGGER = logging.getLogger(__name__)

try:
    mlflow = importlib.import_module("mlflow")
except Exception:
    mlflow = None


def _log_to_mlflow(model_name: str, params: dict[str, Any], enabled: bool) -> None:
    """Log best params to MLflow when enabled and available."""
    if not enabled or mlflow is None:
        return

    with mlflow.start_run(run_name=f"opt_{model_name}"):
        mlflow.log_params({f"{model_name}_{k}": v for k, v in params.items()})


def optimize_models_for_recall(
    svm_model: SVMFraudModel,
    rf_model: RFFraudModel,
    xgb_model: XGBFraudModel,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    cv: int = 5,
    track_with_mlflow: bool = False,
) -> dict[str, dict[str, Any]]:
    """Optimize base model hyperparameters for recall.

    Args:
        svm_model: SVM wrapper.
        rf_model: Random Forest wrapper.
        xgb_model: XGBoost wrapper.
        x_train: Training features.
        y_train: Training labels.
        cv: Number of CV folds.
        track_with_mlflow: Enable optional MLflow experiment tracking.

    Returns:
        Dictionary of best hyperparameters for each model.
    """
    best_svm = svm_model.tune_hyperparameters(x_train=x_train, y_train=y_train, cv=cv)
    best_rf = rf_model.tune_hyperparameters(x_train=x_train, y_train=y_train, cv=cv)
    best_xgb = xgb_model.tune_hyperparameters(x_train=x_train, y_train=y_train, cv=cv)

    _log_to_mlflow("svm", best_svm, track_with_mlflow)
    _log_to_mlflow("random_forest", best_rf, track_with_mlflow)
    _log_to_mlflow("xgboost", best_xgb, track_with_mlflow)

    best_params = {
        "svm": best_svm,
        "random_forest": best_rf,
        "xgboost": best_xgb,
    }
    LOGGER.info("Completed recall-focused optimization for all base models.")
    return best_params
