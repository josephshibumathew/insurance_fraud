"""Batch SHAP explanation generation and caching utilities."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .shap_explainer import GlobalExplanation, LocalExplanation, ShapExplainerEngine

LOGGER = logging.getLogger(__name__)


@dataclass
class ExplanationCache:
    """In-memory cache for reusable explanation artifacts."""

    global_explanations: dict[str, GlobalExplanation] = field(default_factory=dict)


class BatchShapExplainer:
    """Efficient batch explainability with global explanation caching."""

    def __init__(self, explainer_engine: ShapExplainerEngine) -> None:
        self.explainer_engine = explainer_engine
        self.cache = ExplanationCache()

    @staticmethod
    def _hash_matrix(x_data: np.ndarray | pd.DataFrame) -> str:
        arr = x_data.values if isinstance(x_data, pd.DataFrame) else np.asarray(x_data)
        digest = hashlib.sha256(arr.tobytes()).hexdigest()
        return digest

    def explain_batch_local(
        self,
        x_data: np.ndarray | pd.DataFrame,
        predictions: np.ndarray | None = None,
    ) -> list[LocalExplanation]:
        """Generate local explanations for many claims."""
        arr = x_data.values if isinstance(x_data, pd.DataFrame) else np.asarray(x_data)
        if arr.ndim != 2:
            raise ValueError("x_data must be 2D.")

        outputs: list[LocalExplanation] = []
        start = time.perf_counter()
        for index in range(arr.shape[0]):
            pred = float(predictions[index]) if predictions is not None else None
            outputs.append(self.explainer_engine.explain_local(arr[index], prediction=pred))
        elapsed = time.perf_counter() - start
        LOGGER.info("Generated %s local explanations in %.3fs", len(outputs), elapsed)
        return outputs

    def explain_global_cached(
        self,
        x_data: np.ndarray | pd.DataFrame,
        max_samples: int = 500,
    ) -> GlobalExplanation:
        """Generate or retrieve cached global explanation."""
        cache_key = f"{self._hash_matrix(x_data)}_{max_samples}"
        if cache_key in self.cache.global_explanations:
            LOGGER.info("Using cached global SHAP explanation.")
            return self.cache.global_explanations[cache_key]

        global_exp = self.explainer_engine.explain_global(x_data=x_data, max_samples=max_samples)
        self.cache.global_explanations[cache_key] = global_exp
        return global_exp

    def explain(
        self,
        x_data: np.ndarray | pd.DataFrame,
        explanation_type: str = "local",
        predictions: np.ndarray | None = None,
    ) -> dict[str, Any]:
        """Generic explanation entrypoint for local/global modes."""
        explanation_type = explanation_type.lower()
        if explanation_type == "local":
            local_exps = self.explain_batch_local(x_data=x_data, predictions=predictions)
            return {
                "type": "local",
                "count": len(local_exps),
                "items": [
                    {
                        "base_value": item.base_value,
                        "prediction": item.prediction,
                        "mapped_feature_contributions": item.mapped_feature_contributions,
                        "elapsed_seconds": item.elapsed_seconds,
                    }
                    for item in local_exps
                ],
            }

        if explanation_type == "global":
            global_exp = self.explain_global_cached(x_data=x_data)
            return {
                "type": "global",
                "feature_importance": global_exp.feature_importance.to_dict(orient="records"),
                "elapsed_seconds": global_exp.elapsed_seconds,
            }

        raise ValueError("explanation_type must be 'local' or 'global'.")
