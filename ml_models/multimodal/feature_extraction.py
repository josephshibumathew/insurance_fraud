"""Feature extraction for multimodal fraud fusion."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

from ml_models.yolo_module.damage_classifier import DAMAGE_CLASSES, VEHICLE_PARTS, infer_part_from_class_name

LOGGER = logging.getLogger(__name__)

_LOCATION_KEYS = ["front", "rear", "side", "top", "unknown"]


@dataclass
class ImageFeatureBundle:
    """Container for extracted image-derived features."""

    feature_vector: np.ndarray
    feature_names: list[str]
    metadata: dict[str, Any]


def _extract_location_from_detection(det: dict[str, Any]) -> str:
    class_name = str(det.get("class_name", "")).lower()
    if any(key in class_name for key in ["bumper", "headlight", "hood", "windshield"]):
        return "front"
    if "trunk" in class_name:
        return "rear"
    if any(key in class_name for key in ["door", "side_mirror"]):
        return "side"
    if "roof" in class_name:
        return "top"

    bbox = det.get("bbox") or [0, 0, 0, 0]
    if len(bbox) == 4:
        x1, y1, x2, y2 = [float(v) for v in bbox]
        y_center = (y1 + y2) / 2
        if y_center < 200:
            return "top"
        if y_center < 350:
            return "front"
        return "rear"
    return "unknown"


def _claim_consistency_score(claim_description: str | None, detections: list[dict[str, Any]]) -> float:
    if not claim_description:
        return 0.5

    text = claim_description.lower()
    tokens = set(re.findall(r"[a-z_]+", text))

    detected_terms: set[str] = set()
    for det in detections:
        class_name = str(det.get("class_name", "")).lower()
        detected_terms.update(class_name.replace("-", "_").split("_"))
        part = infer_part_from_class_name(class_name)
        if part:
            detected_terms.add(part)

    if not detected_terms:
        return 0.0
    overlap = len(tokens.intersection(detected_terms))
    return round(overlap / max(1, len(detected_terms)), 4)


def extract_image_features(
    yolo_output: dict[str, Any],
    claim_description: str | None = None,
) -> ImageFeatureBundle:
    """Extract fixed-size image features from YOLO outputs.

    Features include damage counts, type distribution, severity score, affected
    part count, location distribution, and text-image consistency score.

    Args:
        yolo_output: Output dictionary from YOLO inference module.
        claim_description: Optional claim narrative for consistency checks.

    Returns:
        ImageFeatureBundle containing feature vector and metadata.
    """
    detections = yolo_output.get("detections", [])

    damage_count = float(len(detections))
    severity_score = float(yolo_output.get("severity_score", 0.0))
    affected_parts = yolo_output.get("affected_parts", [])
    part_count = float(len(set(affected_parts)))

    type_counts = yolo_output.get("count_by_damage_type") or {}
    damage_distribution = np.array(
        [float(type_counts.get(name, 0)) for name in DAMAGE_CLASSES],
        dtype=float,
    )

    location_counts = {key: 0.0 for key in _LOCATION_KEYS}
    for det in detections:
        location_counts[_extract_location_from_detection(det)] += 1.0

    consistency = _claim_consistency_score(claim_description=claim_description, detections=detections)

    feature_names = [
        "total_damage_count",
        *[f"damage_count_{name}" for name in DAMAGE_CLASSES],
        "severity_score",
        "affected_part_count",
        *[f"location_{name}" for name in _LOCATION_KEYS],
        "claim_detection_consistency",
    ]

    feature_vector = np.concatenate(
        [
            np.array([damage_count], dtype=float),
            damage_distribution,
            np.array([severity_score, part_count], dtype=float),
            np.array([location_counts[k] for k in _LOCATION_KEYS], dtype=float),
            np.array([consistency], dtype=float),
        ]
    )

    metadata = {
        "detections": detections,
        "affected_parts": sorted(set(affected_parts)),
        "vehicle_parts_reference": VEHICLE_PARTS,
        "damage_classes_reference": DAMAGE_CLASSES,
    }

    LOGGER.info(
        "Extracted image features | damage_count=%s severity=%.4f part_count=%s",
        int(damage_count),
        severity_score,
        int(part_count),
    )
    return ImageFeatureBundle(feature_vector=feature_vector, feature_names=feature_names, metadata=metadata)


def extract_batch_image_features(
    yolo_outputs: list[dict[str, Any]],
    claim_descriptions: list[str] | None = None,
) -> tuple[np.ndarray, list[str], list[dict[str, Any]]]:
    """Extract feature matrix for multiple claims/images.

    Args:
        yolo_outputs: List of YOLO output dictionaries.
        claim_descriptions: Optional list of claim descriptions aligned with outputs.

    Returns:
        Tuple of feature matrix, feature names, and metadata list.
    """
    if not yolo_outputs:
        raise ValueError("yolo_outputs cannot be empty.")

    if claim_descriptions and len(claim_descriptions) != len(yolo_outputs):
        raise ValueError("claim_descriptions must have same length as yolo_outputs.")

    bundles: list[ImageFeatureBundle] = []
    for index, output in enumerate(yolo_outputs):
        desc = claim_descriptions[index] if claim_descriptions else None
        bundles.append(extract_image_features(output, claim_description=desc))

    matrix = np.vstack([bundle.feature_vector for bundle in bundles])
    return matrix, bundles[0].feature_names, [bundle.metadata for bundle in bundles]
