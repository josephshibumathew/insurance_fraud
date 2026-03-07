"""Evaluation module for YOLO vehicle damage detection."""

from __future__ import annotations

import json
import importlib
import logging
from pathlib import Path
from typing import Any

from sklearn.metrics import confusion_matrix

from .inference import process_single_image
from .utils import draw_bounding_boxes
from .yolo_model import YOLOConfig, YOLOModelWrapper

LOGGER = logging.getLogger(__name__)


def _get_plotting_modules():
    try:
        plt = importlib.import_module("matplotlib.pyplot")
        sns = importlib.import_module("seaborn")
        return plt, sns
    except Exception as exc:
        raise ImportError(
            "matplotlib and seaborn are required for confusion matrix visualization."
        ) from exc


def _parse_label_classes(label_file: Path) -> list[int]:
    if not label_file.exists():
        return []
    classes: list[int] = []
    for line in label_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        try:
            classes.append(int(float(parts[0])))
        except (ValueError, IndexError):
            continue
    return classes


def evaluate_yolo_model(
    weights_path: str | Path,
    data_yaml: str | Path,
    val_images_dir: str | Path,
    val_labels_dir: str | Path,
    class_names: list[str],
    report_dir: str | Path,
    sample_visualizations: int = 5,
) -> dict[str, Any]:
    """Evaluate YOLO model and export metrics/plots.

    Args:
        weights_path: Trained model path.
        data_yaml: data.yaml path.
        val_images_dir: Validation image directory.
        val_labels_dir: Validation labels directory.
        class_names: Model class names.
        report_dir: Output report directory.
        sample_visualizations: Number of samples for prediction visualization.

    Returns:
        Evaluation report dictionary.
    """
    out_dir = Path(report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    wrapper = YOLOModelWrapper(
        weights_path=str(weights_path),
        config=YOLOConfig(imgsz=640, conf_thres=0.25, iou_thres=0.45),
    )
    val_results = wrapper.validate(data_yaml=data_yaml, split="val")

    metrics_dict = getattr(val_results, "results_dict", {})
    report: dict[str, Any] = {
        "map50": float(metrics_dict.get("metrics/mAP50(B)", metrics_dict.get("metrics/mAP50", 0.0))),
        "map50_95": float(metrics_dict.get("metrics/mAP50-95(B)", metrics_dict.get("metrics/mAP50-95", 0.0))),
        "precision": float(metrics_dict.get("metrics/precision(B)", metrics_dict.get("metrics/precision", 0.0))),
        "recall": float(metrics_dict.get("metrics/recall(B)", metrics_dict.get("metrics/recall", 0.0))),
    }

    images_dir = Path(val_images_dir)
    labels_dir = Path(val_labels_dir)
    image_paths = [
        p
        for p in sorted(images_dir.rglob("*"))
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    ]

    y_true: list[int] = []
    y_pred: list[int] = []

    for image in image_paths:
        gt_classes = _parse_label_classes(labels_dir / f"{image.stem}.txt")
        pred = process_single_image(wrapper, image)
        pred_classes = [int(item["class_id"]) for item in pred["detections"]]

        if not gt_classes and not pred_classes:
            continue
        if gt_classes:
            y_true.append(gt_classes[0])
        else:
            y_true.append(-1)

        if pred_classes:
            y_pred.append(pred_classes[0])
        else:
            y_pred.append(-1)

    class_indices = [-1] + list(range(len(class_names)))
    class_labels = ["background"] + class_names

    if y_true and y_pred:
        plt, sns = _get_plotting_modules()
        matrix = confusion_matrix(y_true, y_pred, labels=class_indices)
        plt.figure(figsize=(10, 8))
        sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", xticklabels=class_labels, yticklabels=class_labels)
        plt.title("Damage Type Confusion Matrix")
        plt.xlabel("Predicted")
        plt.ylabel("Actual")
        confusion_path = out_dir / "confusion_matrix.png"
        plt.tight_layout()
        plt.savefig(confusion_path)
        plt.close()
        report["confusion_matrix_path"] = str(confusion_path)
    else:
        report["confusion_matrix_path"] = None

    vis_dir = out_dir / "sample_predictions"
    vis_dir.mkdir(parents=True, exist_ok=True)
    for image in image_paths[:sample_visualizations]:
        try:
            pred = process_single_image(wrapper, image)
            draw_bounding_boxes(image, pred["detections"], vis_dir / image.name)
        except Exception as exc:
            LOGGER.warning("Failed visualization for %s: %s", image, exc)

    report_path = out_dir / "yolo_evaluation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    LOGGER.info("Saved YOLO evaluation report to %s", report_path)
    return report
