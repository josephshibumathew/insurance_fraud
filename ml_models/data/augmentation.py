"""Image preprocessing and augmentation utilities for YOLO pipelines."""

from __future__ import annotations

import logging
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

LOGGER = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png")


def _parse_yolo_labels(label_path: Path) -> list[tuple[int, float, float, float, float]]:
	if not label_path.exists():
		return []
	labels: list[tuple[int, float, float, float, float]] = []
	with label_path.open("r", encoding="utf-8") as fp:
		for line in fp:
			parts = line.strip().split()
			if len(parts) != 5:
				continue
			class_id = int(parts[0])
			x_center, y_center, width, height = map(float, parts[1:])
			labels.append((class_id, x_center, y_center, width, height))
	return labels


def _serialize_yolo_labels(labels: list[tuple[int, float, float, float, float]], output_path: Path) -> None:
	with output_path.open("w", encoding="utf-8") as fp:
		for class_id, x_center, y_center, width, height in labels:
			fp.write(
				f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"
			)


def _transform_bboxes(
	labels: list[tuple[int, float, float, float, float]],
	flip: bool,
	angle_deg: float,
) -> list[tuple[int, float, float, float, float]]:
	transformed: list[tuple[int, float, float, float, float]] = []
	theta = np.deg2rad(angle_deg)
	cos_t, sin_t = np.cos(theta), np.sin(theta)

	for class_id, x_center, y_center, width, height in labels:
		xc = 1.0 - x_center if flip else x_center
		yc = y_center

		half_w = width / 2.0
		half_h = height / 2.0
		corners = np.array(
			[
				[xc - half_w, yc - half_h],
				[xc + half_w, yc - half_h],
				[xc + half_w, yc + half_h],
				[xc - half_w, yc + half_h],
			],
			dtype=float,
		)

		centered = corners - 0.5
		rotated_x = centered[:, 0] * cos_t - centered[:, 1] * sin_t
		rotated_y = centered[:, 0] * sin_t + centered[:, 1] * cos_t
		rotated = np.stack([rotated_x, rotated_y], axis=1) + 0.5
		rotated = np.clip(rotated, 0.0, 1.0)

		x_min, y_min = rotated.min(axis=0)
		x_max, y_max = rotated.max(axis=0)
		new_w = x_max - x_min
		new_h = y_max - y_min
		if new_w <= 0 or new_h <= 0:
			continue

		new_xc = (x_min + x_max) / 2.0
		new_yc = (y_min + y_max) / 2.0
		transformed.append((class_id, float(new_xc), float(new_yc), float(new_w), float(new_h)))

	return transformed


def _augment_image(
	image: Image.Image,
	rng: random.Random,
) -> tuple[Image.Image, bool, float]:
	flip = rng.random() < 0.5
	angle = rng.uniform(-10.0, 10.0)
	brightness_factor = rng.uniform(0.8, 1.2)

	augmented = image
	if flip:
		augmented = ImageOps.mirror(augmented)
	augmented = augmented.rotate(angle, resample=Image.BILINEAR, expand=False)
	augmented = ImageEnhance.Brightness(augmented).enhance(brightness_factor)
	return augmented, flip, angle


def preprocess_yolo_dataset(
	images_dir: str | Path,
	labels_dir: str | Path,
	output_dir: str | Path,
	train_ratio: float = 0.8,
	random_state: int = 42,
	apply_augmentation: bool = True,
) -> dict[str, int]:
	"""Preprocess images and labels into YOLO-ready train/val structure.

	Args:
		images_dir: Input image directory.
		labels_dir: Input YOLO label directory.
		output_dir: Output root directory for YOLO format.
		train_ratio: Ratio for training split.
		random_state: Seed for deterministic splitting and augmentation.
		apply_augmentation: Whether to apply augmentations to train images.

	Returns:
		Summary counts of generated training and validation samples.

	Raises:
		FileNotFoundError: If images directory does not exist.
		ValueError: If no supported images are found.
	"""
	in_images = Path(images_dir)
	in_labels = Path(labels_dir)
	out_root = Path(output_dir)

	if not in_images.exists():
		raise FileNotFoundError(f"Input images directory not found: {in_images}")

	image_files = sorted(
		[
			path
			for path in in_images.rglob("*")
			if path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
		]
	)
	if not image_files:
		raise ValueError("No supported image files found for YOLO preprocessing.")

	rng = random.Random(random_state)
	rng.shuffle(image_files)
	train_count = int(len(image_files) * train_ratio)
	train_set = set(image_files[:train_count])

	for split in ("train", "val"):
		(out_root / "images" / split).mkdir(parents=True, exist_ok=True)
		(out_root / "labels" / split).mkdir(parents=True, exist_ok=True)

	generated_train = 0
	generated_val = 0

	for image_path in image_files:
		split = "train" if image_path in train_set else "val"
		label_path = in_labels / f"{image_path.stem}.txt"
		labels = _parse_yolo_labels(label_path)

		with Image.open(image_path) as img:
			rgb_image = img.convert("RGB")
			if split == "train" and apply_augmentation:
				rgb_image, flip, angle = _augment_image(rgb_image, rng=rng)
				labels = _transform_bboxes(labels=labels, flip=flip, angle_deg=angle)

			resized = rgb_image.resize((640, 640), Image.BILINEAR)
			normalized = np.asarray(resized, dtype=np.float32) / 255.0
			output_pixels = np.clip(normalized * 255.0, 0, 255).astype(np.uint8)
			output_image = Image.fromarray(output_pixels)

		output_image_path = out_root / "images" / split / f"{image_path.stem}.jpg"
		output_label_path = out_root / "labels" / split / f"{image_path.stem}.txt"

		output_image.save(output_image_path, format="JPEG", quality=95)
		_serialize_yolo_labels(labels, output_label_path)

		if split == "train":
			generated_train += 1
		else:
			generated_val += 1

	summary = {"train_images": generated_train, "val_images": generated_val}
	LOGGER.info("YOLO preprocessing complete: %s", summary)
	return summary

