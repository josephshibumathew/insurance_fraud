"""Train YOLOv11 model from claim folder images under raw/training and raw/validation."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from ml_models.yolo_module.dataset_preparation import prepare_yolo_dataset
from ml_models.yolo_module.train import train_yolo_damage_detector


LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def _configure_logging() -> None:
	if not logging.getLogger().handlers:
		logging.basicConfig(
			level=logging.INFO,
			format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
		)


def _resolve_class_map(images_root: Path) -> dict[str, int]:
	class_dirs: set[str] = set()
	for split in ("training", "validation"):
		split_dir = images_root / split
		if not split_dir.exists():
			continue
		for child in split_dir.iterdir():
			if child.is_dir() and child.name.lower().startswith("claim_"):
				class_dirs.add(child.name)

	if not class_dirs:
		raise ValueError(f"No claim_* class folders found in {images_root}/training or validation")

	return {name: index for index, name in enumerate(sorted(class_dirs))}


def _build_pseudo_bbox_annotations(images_root: Path, annotation_csv: Path) -> tuple[pd.DataFrame, list[str]]:
	"""Create synthetic full-image bounding boxes for claim folder classes.

	This enables YOLO detection training even when only class-folders are available.
	"""
	try:
		from PIL import Image
	except Exception as exc:
		raise ImportError("Pillow is required to compute image dimensions for YOLO annotations.") from exc

	class_map = _resolve_class_map(images_root)
	rows: list[dict[str, Any]] = []

	for split in ("training", "validation"):
		split_dir = images_root / split
		if not split_dir.exists():
			continue
		for class_dir in sorted([path for path in split_dir.iterdir() if path.is_dir()]):
			if class_dir.name not in class_map:
				continue
			for image_path in sorted(class_dir.rglob("*")):
				if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
					continue
				with Image.open(image_path) as image:
					width, height = image.size
				if width <= 1 or height <= 1:
					continue

				rel_image = image_path.relative_to(images_root).as_posix()
				rows.append(
					{
						"image": rel_image,
						"class_name": class_dir.name,
						"x_min": 0,
						"y_min": 0,
						"x_max": width,
						"y_max": height,
						"width": width,
						"height": height,
					}
				)

	if not rows:
		raise ValueError(f"No supported images found in {images_root}")

	dataframe = pd.DataFrame(rows)
	annotation_csv.parent.mkdir(parents=True, exist_ok=True)
	dataframe.to_csv(annotation_csv, index=False)
	class_names = [name for name, _ in sorted(class_map.items(), key=lambda item: item[1])]
	LOGGER.info("Created pseudo YOLO annotations at %s for %s images", annotation_csv, len(dataframe))
	return dataframe, class_names


def run_training(
	images_root: str | Path,
	output_model: str | Path,
	epochs: int = 20,
	batch: int = 16,
	lr0: float = 0.005,
) -> dict[str, Any]:
	_configure_logging()
	package_root = Path(__file__).resolve().parents[1]

	images_root_path = Path(images_root)
	output_model_path = Path(output_model)
	output_model_path.parent.mkdir(parents=True, exist_ok=True)

	yolo_dataset_root = package_root / "data" / "yolo_format"
	annotation_csv = yolo_dataset_root / "annotations_from_claim_folders.csv"

	_, class_names = _build_pseudo_bbox_annotations(images_root_path, annotation_csv=annotation_csv)

	prepare_summary = prepare_yolo_dataset(
		source_images_dir=images_root_path,
		output_root=yolo_dataset_root,
		class_names=class_names,
		annotation_csv=annotation_csv,
		train_ratio=0.8,
		random_state=42,
	)

	project_dir = package_root / "models" / "yolo" / "runs"
	train_summary = train_yolo_damage_detector(
		data_yaml=prepare_summary["data_yaml"],
		weights="yolo11n.pt",
		output_model_path=output_model_path,
		epochs=epochs,
		batch=batch,
		lr0=lr0,
		optimizer="AdamW",
		augment=True,
		patience=max(5, min(10, epochs // 2)),
		project=project_dir,
		run_name="yolo_claim_folder_training",
	)

	script_summary = {
		"class_names": class_names,
		"dataset_prep": prepare_summary,
		"training": train_summary,
	}
	summary_path = output_model_path.parent / "train_yolo_script_summary.json"
	summary_path.write_text(json.dumps(script_summary, indent=2), encoding="utf-8")
	LOGGER.info("Saved script summary to %s", summary_path)
	return script_summary


def build_arg_parser() -> argparse.ArgumentParser:
	package_root = Path(__file__).resolve().parents[1]
	parser = argparse.ArgumentParser(description="Train YOLOv11 from claim folder images.")
	parser.add_argument(
		"--images-root",
		type=str,
		default=str(package_root / "data" / "raw" / "images"),
		help="Root images directory containing training/validation claim_* folders.",
	)
	parser.add_argument(
		"--output-model",
		type=str,
		default=str(package_root / "models" / "yolo" / "best.pt"),
		help="Output path for YOLO best weights.",
	)
	parser.add_argument("--epochs", type=int, default=20, help="Training epochs.")
	parser.add_argument("--batch", type=int, default=16, help="Batch size.")
	parser.add_argument("--lr0", type=float, default=0.005, help="Initial learning rate.")
	return parser


if __name__ == "__main__":
	args = build_arg_parser().parse_args()
	run_training(
		images_root=args.images_root,
		output_model=args.output_model,
		epochs=args.epochs,
		batch=args.batch,
		lr0=args.lr0,
	)
