"""Inference utilities for YOLO-based vehicle damage detection."""

from __future__ import annotations

import json
import importlib
import logging
from pathlib import Path
from typing import Any

from .damage_classifier import aggregate_damage_features
from .utils import filter_detections_by_confidence, validate_supported_image
from .yolo_model import YOLOModelWrapper

LOGGER = logging.getLogger(__name__)


def _validate_image_readable(image_path: Path) -> None:
	try:
		image_module = importlib.import_module("PIL.Image")
		with image_module.open(image_path) as img:
			img.verify()
	except Exception as exc:
		raise ValueError(f"Corrupted or unreadable image file: {image_path}") from exc


def _result_to_detections(result, class_names: dict[int, str] | list[str] | None = None) -> list[dict[str, Any]]:
	detections: list[dict[str, Any]] = []
	boxes = getattr(result, "boxes", None)
	if boxes is None:
		return detections

	names = class_names if class_names is not None else getattr(result, "names", {})
	xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes, "xyxy") else []
	conf = boxes.conf.cpu().numpy() if hasattr(boxes, "conf") else []
	cls = boxes.cls.cpu().numpy() if hasattr(boxes, "cls") else []

	for bbox, score, class_id in zip(xyxy, conf, cls):
		class_idx = int(class_id)
		if isinstance(names, dict):
			class_name = str(names.get(class_idx, f"class_{class_idx}"))
		else:
			class_name = str(names[class_idx]) if class_idx < len(names) else f"class_{class_idx}"

		detections.append(
			{
				"class_id": class_idx,
				"class_name": class_name,
				"confidence": float(score),
				"bbox": [float(v) for v in bbox.tolist()],
			}
		)

	return detections


def process_single_image(
	model_wrapper: YOLOModelWrapper,
	image_path: str | Path,
	conf_threshold: float = 0.25,
) -> dict[str, Any]:
	"""Run inference on a single image and return structured output.

	Args:
		model_wrapper: Initialized YOLO model wrapper.
		image_path: Path to image.
		conf_threshold: Confidence threshold for filtering detections.

	Returns:
		Structured prediction dictionary for multimodal fusion.
	"""
	image = Path(image_path)
	if not image.exists():
		raise FileNotFoundError(f"Image not found: {image}")
	if not validate_supported_image(image):
		raise ValueError(f"Unsupported image format: {image.suffix}")
	_validate_image_readable(image)

	try:
		results = model_wrapper.predict(source=str(image))
	except Exception as exc:
		raise RuntimeError(f"YOLO inference failed for {image}: {exc}") from exc

	if not results:
		detections: list[dict[str, Any]] = []
	else:
		detections = _result_to_detections(results[0])
	detections = filter_detections_by_confidence(detections, min_confidence=conf_threshold)

	features = aggregate_damage_features(detections)
	output = {
		"image_path": str(image),
		"detections": detections,
		"count_by_damage_type": features.count_by_damage_type,
		"severity_score": features.severity_score,
		"affected_parts": features.affected_parts,
	}
	return output


def process_batch_images(
	model_wrapper: YOLOModelWrapper,
	image_paths: list[str | Path],
	conf_threshold: float = 0.25,
	output_json_path: str | Path | None = None,
) -> dict[str, Any]:
	"""Run batch inference on multiple images.

	Args:
		model_wrapper: Initialized YOLO model wrapper.
		image_paths: List of image paths.
		conf_threshold: Confidence threshold for filtering detections.
		output_json_path: Optional path to store JSON output.

	Returns:
		Dictionary containing image-level and aggregate batch features.
	"""
	if not image_paths:
		raise ValueError("image_paths cannot be empty.")

	valid_paths: list[Path] = []
	invalid_paths: list[str] = []
	for path in image_paths:
		p = Path(path)
		if not p.exists() or not validate_supported_image(p):
			invalid_paths.append(str(p))
			continue
		valid_paths.append(p)

	if not valid_paths:
		raise ValueError("No valid image paths found for inference.")

	outputs: list[dict[str, Any]] = []
	for image in valid_paths:
		try:
			outputs.append(process_single_image(model_wrapper, image, conf_threshold=conf_threshold))
		except Exception as exc:
			LOGGER.warning("Skipping image %s due to error: %s", image, exc)
			invalid_paths.append(str(image))

	total_counts: dict[str, int] = {}
	total_severity = 0.0
	affected_parts: set[str] = set()
	for item in outputs:
		total_severity += float(item["severity_score"])
		affected_parts.update(item["affected_parts"])
		for key, value in item["count_by_damage_type"].items():
			total_counts[key] = total_counts.get(key, 0) + int(value)

	payload = {
		"items": outputs,
		"batch_summary": {
			"count_by_damage_type": total_counts,
			"severity_score": round(total_severity, 4),
			"affected_parts": sorted(affected_parts),
			"processed_images": len(outputs),
			"skipped_images": invalid_paths,
		},
	}

	if output_json_path:
		out_path = Path(output_json_path)
		out_path.parent.mkdir(parents=True, exist_ok=True)
		out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
		LOGGER.info("Saved batch inference output to %s", out_path)

	return payload

