"""Damage classification and severity aggregation utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

LOGGER = logging.getLogger(__name__)

DAMAGE_CLASSES: list[str] = [
	"dent",
	"scratch",
	"smash",
	"broken_glass",
	"damaged_bumper",
	"damaged_headlight",
	"damaged_door",
	"damaged_hood",
	"damaged_windshield",
]

VEHICLE_PARTS: list[str] = [
	"bumper",
	"headlight",
	"door",
	"hood",
	"windshield",
	"trunk",
	"roof",
	"side_mirror",
]

_DAMAGE_SEVERITY_WEIGHTS: dict[str, float] = {
	"scratch": 1.0,
	"dent": 2.0,
	"broken_glass": 3.5,
	"smash": 4.0,
	"damaged_headlight": 2.5,
	"damaged_bumper": 2.5,
	"damaged_door": 2.5,
	"damaged_hood": 3.0,
	"damaged_windshield": 3.5,
}

_PART_MULTIPLIER: dict[str, float] = {
	"windshield": 1.3,
	"headlight": 1.2,
	"hood": 1.15,
	"door": 1.1,
	"bumper": 1.05,
	"trunk": 1.05,
	"roof": 1.2,
	"side_mirror": 1.1,
}


@dataclass
class DamageFeatures:
	"""Aggregated detection-level damage features."""

	count_by_damage_type: dict[str, int]
	severity_score: float
	affected_parts: list[str]


def infer_part_from_class_name(class_name: str) -> str | None:
	"""Infer vehicle part based on class naming convention.

	Args:
		class_name: Detected class name.

	Returns:
		Inferred part name if available.
	"""
	lowered = class_name.lower()
	for part in VEHICLE_PARTS:
		if part in lowered:
			return part
	return None


def _get_damage_weight(class_name: str) -> float:
	name = class_name.lower()
	if name in _DAMAGE_SEVERITY_WEIGHTS:
		return _DAMAGE_SEVERITY_WEIGHTS[name]
	if name.startswith("damaged_"):
		return 2.2
	return 1.0


def aggregate_damage_features(detections: list[dict[str, Any]]) -> DamageFeatures:
	"""Aggregate detection outputs to damage-level features.

	Args:
		detections: Detection dictionaries containing class_name and confidence.

	Returns:
		DamageFeatures object.
	"""
	counts: dict[str, int] = {name: 0 for name in DAMAGE_CLASSES}
	affected_parts: set[str] = set()
	total_score = 0.0

	for det in detections:
		class_name = str(det.get("class_name", "unknown"))
		confidence = float(det.get("confidence", 0.0))

		if class_name in counts:
			counts[class_name] += 1
		elif class_name.startswith("damaged_"):
			counts.setdefault(class_name, 0)
			counts[class_name] += 1

		part = infer_part_from_class_name(class_name)
		if part:
			affected_parts.add(part)

		damage_weight = _get_damage_weight(class_name)
		part_weight = _PART_MULTIPLIER.get(part, 1.0) if part else 1.0
		total_score += confidence * damage_weight * part_weight

	severity_score = round(total_score, 4)
	LOGGER.info("Aggregated damage features | severity_score=%.4f", severity_score)
	return DamageFeatures(
		count_by_damage_type=counts,
		severity_score=severity_score,
		affected_parts=sorted(affected_parts),
	)

