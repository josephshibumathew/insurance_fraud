"""Dataset preparation utilities for YOLO vehicle damage detection."""

from __future__ import annotations

import json
import logging
import random
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def _convert_xyxy_to_yolo(
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    box_w = max(0.0, x_max - x_min)
    box_h = max(0.0, y_max - y_min)
    x_c = x_min + box_w / 2
    y_c = y_min + box_h / 2
    return x_c / width, y_c / height, box_w / width, box_h / height


def _parse_csv_annotations(
    csv_path: Path,
    class_to_id: dict[str, int],
) -> dict[str, list[str]]:
    import pandas as pd

    required_columns = {"image", "class_name", "x_min", "y_min", "x_max", "y_max", "width", "height"}
    df = pd.read_csv(csv_path)
    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"CSV annotation schema invalid. Missing columns: {sorted(required_columns - set(df.columns))}"
        )

    entries: dict[str, list[str]] = defaultdict(list)
    for _, row in df.iterrows():
        class_name = str(row["class_name"])
        if class_name not in class_to_id:
            continue
        class_id = class_to_id[class_name]
        x_c, y_c, w, h = _convert_xyxy_to_yolo(
            float(row["x_min"]),
            float(row["y_min"]),
            float(row["x_max"]),
            float(row["y_max"]),
            int(row["width"]),
            int(row["height"]),
        )
        entries[str(row["image"])].append(f"{class_id} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")
    return entries


def _parse_coco_annotations(
    json_path: Path,
    class_to_id: dict[str, int],
) -> dict[str, list[str]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    images = {int(item["id"]): item for item in payload.get("images", [])}
    categories = {int(item["id"]): str(item["name"]) for item in payload.get("categories", [])}

    entries: dict[str, list[str]] = defaultdict(list)
    for ann in payload.get("annotations", []):
        image_info = images.get(int(ann["image_id"]))
        if image_info is None:
            continue
        class_name = categories.get(int(ann["category_id"]), "")
        if class_name not in class_to_id:
            continue

        x, y, w, h = ann.get("bbox", [0, 0, 0, 0])
        width = int(image_info.get("width", 1))
        height = int(image_info.get("height", 1))
        x_c = (x + w / 2) / width
        y_c = (y + h / 2) / height
        w_n = w / width
        h_n = h / height

        entries[str(image_info["file_name"])].append(
            f"{class_to_id[class_name]} {x_c:.6f} {y_c:.6f} {w_n:.6f} {h_n:.6f}"
        )
    return entries


def _copy_existing_yolo_labels(labels_dir: Path) -> dict[str, list[str]]:
    entries: dict[str, list[str]] = {}
    for label_path in labels_dir.glob("*.txt"):
        entries[label_path.stem] = label_path.read_text(encoding="utf-8").strip().splitlines()
    return entries


def prepare_yolo_dataset(
    source_images_dir: str | Path,
    output_root: str | Path,
    class_names: list[str],
    annotation_csv: str | Path | None = None,
    annotation_coco_json: str | Path | None = None,
    existing_yolo_labels_dir: str | Path | None = None,
    train_ratio: float = 0.8,
    random_state: int = 42,
) -> dict[str, str]:
    """Prepare dataset in YOLO format and split into train/val.

    Args:
        source_images_dir: Input image directory. Supports either:
            1) flat folder of images (random train/val split), or
            2) pre-split folders: training/<class_or_claim_folder>/* and validation/<class_or_claim_folder>/*.
        output_root: Output YOLO dataset root.
        class_names: Class list used for class_id mapping.
        annotation_csv: Optional annotation CSV path.
        annotation_coco_json: Optional COCO annotation JSON path.
        existing_yolo_labels_dir: Optional existing YOLO labels directory.
        train_ratio: Train split ratio.
        random_state: Random seed.

    Returns:
        Dictionary containing generated paths including data.yaml.
    """
    image_dir = Path(source_images_dir)
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")

    output = Path(output_root)
    for split in ("train", "val"):
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)

    class_to_id = {name: index for index, name in enumerate(class_names)}

    annotation_entries: dict[str, list[str]] = {}
    if annotation_csv:
        annotation_entries = _parse_csv_annotations(Path(annotation_csv), class_to_id=class_to_id)
    elif annotation_coco_json:
        annotation_entries = _parse_coco_annotations(Path(annotation_coco_json), class_to_id=class_to_id)
    elif existing_yolo_labels_dir:
        annotation_entries = _copy_existing_yolo_labels(Path(existing_yolo_labels_dir))
    else:
        LOGGER.warning(
            "No annotation source provided; generating empty YOLO label files for all images."
        )

    valid_ext = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    training_root = image_dir / "training"
    validation_root = image_dir / "validation"
    has_presplit = training_root.exists() and validation_root.exists()

    images = [path for path in sorted(image_dir.rglob("*")) if path.suffix.lower() in valid_ext]
    if not images:
        raise ValueError(f"No supported images found in: {image_dir}")

    train_set: set[Path] = set()
    if has_presplit:
        train_set = {
            path
            for path in images
            if training_root in path.parents
        }
    else:
        rng = random.Random(random_state)
        rng.shuffle(images)
        train_count = int(len(images) * train_ratio)
        train_set = set(images[:train_count])

    copied_train = 0
    copied_val = 0
    for image_path in images:
        split = "train" if image_path in train_set else "val"
        relative_token = "_".join(image_path.relative_to(image_dir).parts)
        destination_name = relative_token.replace(" ", "_")
        destination_image = output / "images" / split / destination_name
        shutil.copy2(image_path, destination_image)

        key_candidates = [
            image_path.name,
            image_path.stem,
            str(image_path.relative_to(image_dir)),
            str(image_path.relative_to(image_dir)).replace("\\", "/"),
        ]
        labels = []
        for key in key_candidates:
            if key in annotation_entries:
                labels = annotation_entries[key]
                break

        label_file = output / "labels" / split / f"{Path(destination_name).stem}.txt"
        label_file.write_text("\n".join(labels) + ("\n" if labels else ""), encoding="utf-8")

        if split == "train":
            copied_train += 1
        else:
            copied_val += 1

    data_yaml_path = output / "data.yaml"
    yaml_lines = [
        f"path: {str(output.resolve())}",
        "train: images/train",
        "val: images/val",
        f"nc: {len(class_names)}",
        "names:",
    ]
    yaml_lines.extend([f"  - {name}" for name in class_names])
    data_yaml_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    LOGGER.info(
        "Prepared YOLO dataset | train=%s val=%s data_yaml=%s",
        copied_train,
        copied_val,
        data_yaml_path,
    )

    return {
        "dataset_root": str(output),
        "data_yaml": str(data_yaml_path),
        "train_images": str(copied_train),
        "val_images": str(copied_val),
    }
