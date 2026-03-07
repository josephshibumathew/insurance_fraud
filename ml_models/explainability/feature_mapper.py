"""Feature mapping utilities for one-hot encoded fraud model features."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

LOGGER = logging.getLogger(__name__)


@dataclass
class MappedFeature:
    """Mapped human-readable feature representation."""

    original_group: str
    encoded_feature: str
    feature_value: float
    shap_value: float
    description: str


class FeatureMapper:
    """Map engineered feature names back to human-readable groups."""

    def __init__(self, feature_names: list[str]) -> None:
        self.feature_names = feature_names

    @staticmethod
    def _simplify_name(name: str) -> str:
        cleaned = name
        for prefix in ["categorical__", "numerical__", "remainder__", "onehot__"]:
            cleaned = cleaned.replace(prefix, "")
        cleaned = cleaned.replace("__", "_")
        return cleaned

    @staticmethod
    def _group_name(simplified_name: str) -> str:
        if "_" not in simplified_name:
            return simplified_name

        if any(token in simplified_name for token in ["policy_type", "accident_location", "vehicle"]):
            key_tokens = ["policy_type", "accident_location", "vehicle_age", "vehicle_type", "vehicle_make"]
            for token in key_tokens:
                if token in simplified_name:
                    return token

        parts = simplified_name.split("_")
        if len(parts) > 1:
            return "_".join(parts[:-1])
        return simplified_name

    @staticmethod
    def _description(group: str) -> str:
        readable = group.replace("_", " ")
        return f"Feature group related to {readable}."

    def map_feature_name(self, encoded_name: str) -> tuple[str, str]:
        simplified = self._simplify_name(encoded_name)
        group = self._group_name(simplified)
        return group, simplified

    def map_contributions(
        self,
        feature_names: list[str],
        shap_values: np.ndarray,
        feature_values: np.ndarray,
    ) -> list[dict[str, Any]]:
        """Map raw SHAP contributions into grouped and readable format."""
        mapped: list[dict[str, Any]] = []
        for name, shap_value, feat_value in zip(feature_names, shap_values, feature_values):
            group, simplified = self.map_feature_name(name)
            mapped.append(
                {
                    "original_group": group,
                    "encoded_feature": simplified,
                    "feature_value": float(feat_value),
                    "shap_value": float(shap_value),
                    "description": self._description(group),
                }
            )

        mapped.sort(key=lambda row: abs(row["shap_value"]), reverse=True)
        return mapped

    def group_related_features(
        self,
        mapped_contributions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Aggregate mapped feature contributions by original group."""
        grouped: dict[str, dict[str, Any]] = {}
        for row in mapped_contributions:
            group = str(row["original_group"])
            grouped.setdefault(
                group,
                {
                    "group": group,
                    "total_shap_value": 0.0,
                    "member_features": [],
                    "description": self._description(group),
                },
            )
            grouped[group]["total_shap_value"] += float(row["shap_value"])
            grouped[group]["member_features"].append(row["encoded_feature"])

        values = list(grouped.values())
        values.sort(key=lambda item: abs(item["total_shap_value"]), reverse=True)
        return values
