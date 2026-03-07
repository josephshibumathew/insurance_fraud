"""Utility functions for YOLO-based vehicle damage detection."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

LOGGER = logging.getLogger(__name__)

try:
	import cv2
except Exception:
	cv2 = None


def yolo_to_xyxy(
	x_center: float,
	y_center: float,
	width: float,
	height: float,
	image_width: int,
	image_height: int,
) -> tuple[int, int, int, int]:
	"""Convert normalized YOLO bbox into absolute xyxy coordinates."""
	x_c = x_center * image_width
	y_c = y_center * image_height
	w = width * image_width
	h = height * image_height
	x1 = int(max(0, x_c - w / 2))
	y1 = int(max(0, y_c - h / 2))
	x2 = int(min(image_width, x_c + w / 2))
	y2 = int(min(image_height, y_c + h / 2))
	return x1, y1, x2, y2


def xyxy_to_yolo(
	x1: float,
	y1: float,
	x2: float,
	y2: float,
	image_width: int,
	image_height: int,
) -> tuple[float, float, float, float]:
	"""Convert absolute xyxy coordinates to normalized YOLO format."""
	box_w = max(0.0, x2 - x1)
	box_h = max(0.0, y2 - y1)
	x_c = x1 + box_w / 2
	y_c = y1 + box_h / 2
	return (
		x_c / image_width,
		y_c / image_height,
		box_w / image_width,
		box_h / image_height,
	)


def filter_detections_by_confidence(
	detections: list[dict[str, Any]],
	min_confidence: float,
) -> list[dict[str, Any]]:
	"""Filter detections by confidence threshold."""
	return [det for det in detections if float(det.get("confidence", 0.0)) >= min_confidence]


def calculate_iou(box_a: list[float] | tuple[float, float, float, float], box_b: list[float] | tuple[float, float, float, float]) -> float:
	"""Compute IoU between two xyxy boxes."""
	ax1, ay1, ax2, ay2 = box_a
	bx1, by1, bx2, by2 = box_b

	inter_x1 = max(ax1, bx1)
	inter_y1 = max(ay1, by1)
	inter_x2 = min(ax2, bx2)
	inter_y2 = min(ay2, by2)

	inter_w = max(0.0, inter_x2 - inter_x1)
	inter_h = max(0.0, inter_y2 - inter_y1)
	inter_area = inter_w * inter_h

	area_a = max(0.0, (ax2 - ax1)) * max(0.0, (ay2 - ay1))
	area_b = max(0.0, (bx2 - bx1)) * max(0.0, (by2 - by1))
	union = area_a + area_b - inter_area
	if union <= 0:
		return 0.0
	return float(inter_area / union)


def draw_bounding_boxes(
	image_path: str | Path,
	detections: list[dict[str, Any]],
	output_path: str | Path,
	color: tuple[int, int, int] = (0, 255, 0),
) -> Path:
	"""Draw bounding boxes and labels on an image and save visualization.

	Raises:
		ImportError: If OpenCV is not installed.
		ValueError: If image cannot be loaded.
	"""
	if cv2 is None:
		raise ImportError("opencv-python is required for visualization utilities.")

	image = cv2.imread(str(image_path))
	if image is None:
		raise ValueError(f"Unable to read image file: {image_path}")

	for det in detections:
		bbox = det.get("bbox", [0, 0, 0, 0])
		x1, y1, x2, y2 = map(int, bbox)
		label = f"{det.get('class_name', 'unknown')}:{float(det.get('confidence', 0.0)):.2f}"

		cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
		cv2.putText(
			image,
			label,
			(x1, max(0, y1 - 8)),
			cv2.FONT_HERSHEY_SIMPLEX,
			0.5,
			color,
			1,
			cv2.LINE_AA,
		)

	output = Path(output_path)
	output.parent.mkdir(parents=True, exist_ok=True)
	cv2.imwrite(str(output), image)
	LOGGER.info("Saved visualization to %s", output)
	return output


def validate_supported_image(image_path: str | Path) -> bool:
	"""Validate image format support by extension."""
	suffix = Path(image_path).suffix.lower()
	return suffix in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

