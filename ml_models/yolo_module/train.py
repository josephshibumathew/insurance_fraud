"""Training entrypoint for YOLOv11 vehicle damage detection."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from .yolo_model import YOLOConfig, YOLOModelWrapper

LOGGER = logging.getLogger(__name__)


DEFAULT_WEIGHTS = "yolo11n.pt"


def _configure_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )


def _extract_train_metrics(results: Any) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {
        "map50": None,
        "map50_95": None,
        "precision": None,
        "recall": None,
    }

    names = {
        "map50": ["metrics/mAP50(B)", "metrics/mAP50"],
        "map50_95": ["metrics/mAP50-95(B)", "metrics/mAP50-95"],
        "precision": ["metrics/precision(B)", "metrics/precision"],
        "recall": ["metrics/recall(B)", "metrics/recall"],
    }

    for metric_name, key_options in names.items():
        for key in key_options:
            value = getattr(results, "results_dict", {}).get(key)
            if value is not None:
                metrics[metric_name] = float(value)
                break

    return metrics


def train_yolo_damage_detector(
    data_yaml: str | Path,
    weights: str = DEFAULT_WEIGHTS,
    output_model_path: str | Path | None = None,
    epochs: int = 100,
    batch: int = 16,
    lr0: float = 0.01,
    optimizer: str = "AdamW",
    augment: bool = True,
    patience: int = 10,
    project: str | Path | None = None,
    run_name: str = "yolo_vehicle_damage",
) -> dict[str, Any]:
    """Train YOLOv11 model and export best weights.

    Args:
        data_yaml: YOLO data.yaml path.
        weights: Pre-trained weights name/path.
        output_model_path: Best model destination path.
        epochs: Number of epochs.
        batch: Batch size.
        lr0: Initial learning rate.
        optimizer: Optimizer.
        augment: Enable augmentations.
        patience: Early stopping patience.
        project: Ultralytics project output directory.
        run_name: Ultralytics run name.

    Returns:
        Training summary dictionary.
    """
    _configure_logging()

    package_root = Path(__file__).resolve().parents[1]
    model_output = (
        Path(output_model_path)
        if output_model_path
        else package_root / "models" / "yolo" / "best.pt"
    )
    model_output.parent.mkdir(parents=True, exist_ok=True)

    wrapper = YOLOModelWrapper(
        weights_path=weights,
        config=YOLOConfig(imgsz=640, conf_thres=0.25, iou_thres=0.45),
    )

    results = wrapper.train(
        data_yaml=data_yaml,
        epochs=epochs,
        batch=batch,
        lr0=lr0,
        optimizer=optimizer,
        augment=augment,
        patience=patience,
        project=project,
        name=run_name,
    )

    save_dir = Path(getattr(results, "save_dir", ""))
    best_candidate = save_dir / "weights" / "best.pt"
    if not best_candidate.exists():
        raise FileNotFoundError(f"Training completed but best weights not found at {best_candidate}")

    shutil.copy2(best_candidate, model_output)
    LOGGER.info("Saved best YOLO model to %s", model_output)

    metric_summary = _extract_train_metrics(results)
    summary = {
        "weights_source": weights,
        "data_yaml": str(data_yaml),
        "epochs": epochs,
        "batch": batch,
        "lr0": lr0,
        "optimizer": optimizer,
        "augment": augment,
        "patience": patience,
        "best_model_path": str(model_output),
        "train_metrics": metric_summary,
    }

    metrics_path = model_output.parent / "training_metrics.json"
    metrics_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    LOGGER.info("Saved training metrics to %s", metrics_path)

    return summary


if __name__ == "__main__":
    default_data_yaml = Path(__file__).resolve().parents[1] / "data" / "yolo_format" / "data.yaml"
    if default_data_yaml.exists():
        train_yolo_damage_detector(data_yaml=default_data_yaml)
    else:
        LOGGER.error("Default data.yaml not found: %s", default_data_yaml)
