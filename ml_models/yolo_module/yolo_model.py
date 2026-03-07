"""YOLO model wrapper for vehicle damage detection."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

LOGGER = logging.getLogger(__name__)


class YOLOBackend(Protocol):
	"""Protocol describing required YOLO backend operations."""

	def train(self, **kwargs):
		...

	def predict(self, source, **kwargs):
		...

	def val(self, **kwargs):
		...


def _get_yolo_class():
	"""Dynamically import Ultralytics YOLO class.

	Returns:
		YOLO class object.

	Raises:
		ImportError: If ultralytics is unavailable.
	"""
	try:
		ultralytics_module = importlib.import_module("ultralytics")
		return getattr(ultralytics_module, "YOLO")
	except Exception as exc:
		raise ImportError(
			"ultralytics is required for YOLOv11 functionality. "
			"Install it with `pip install ultralytics`."
		) from exc


@dataclass
class YOLOConfig:
	"""Configuration for YOLO model operations."""

	imgsz: int = 640
	conf_thres: float = 0.25
	iou_thres: float = 0.45
	device: str | int | None = None
	extra_predict_args: dict[str, Any] = field(default_factory=dict)


class YOLOModelWrapper:
	"""YOLOv11 model wrapper for training, inference, and validation.

	The wrapper isolates backend specifics to support future model swapping.
	"""

	def __init__(self, weights_path: str | Path = "yolo11n.pt", config: YOLOConfig | None = None) -> None:
		self.weights_path = str(weights_path)
		self.config = config or YOLOConfig()
		self.model: YOLOBackend | None = None

	def load_model(self) -> None:
		"""Load YOLO model from weights path.

		Raises:
			FileNotFoundError: If local custom weights path is missing.
			RuntimeError: If model initialization fails.
		"""
		weights = Path(self.weights_path)
		if weights.suffix == ".pt" and weights.exists() is False and "/" in self.weights_path:
			raise FileNotFoundError(f"Weights file not found: {weights}")

		try:
			yolo_class = _get_yolo_class()
			self.model = yolo_class(self.weights_path)
			LOGGER.info("Loaded YOLO model with weights: %s", self.weights_path)
		except Exception as exc:
			raise RuntimeError(f"Failed to initialize YOLO model: {exc}") from exc

	def _ensure_model(self) -> YOLOBackend:
		if self.model is None:
			self.load_model()
		return self.model  # type: ignore[return-value]

	def train(
		self,
		data_yaml: str | Path,
		epochs: int = 100,
		batch: int = 16,
		lr0: float = 0.01,
		optimizer: str = "AdamW",
		augment: bool = True,
		patience: int = 10,
		project: str | Path | None = None,
		name: str = "yolo_vehicle_damage",
		**kwargs: Any,
	):
		"""Train YOLO model.

		Args:
			data_yaml: Dataset YAML path.
			epochs: Number of epochs.
			batch: Batch size.
			lr0: Initial learning rate.
			optimizer: Optimizer name.
			augment: Enable augmentation.
			patience: Early stopping patience.
			project: Ultralytics output project directory.
			name: Training run name.
			**kwargs: Extra Ultralytics train parameters.

		Returns:
			Ultralytics training results object.
		"""
		model = self._ensure_model()
		data_yaml_path = Path(data_yaml)
		if not data_yaml_path.exists():
			raise FileNotFoundError(f"Data YAML not found: {data_yaml_path}")

		LOGGER.info(
			"Starting YOLO training | epochs=%s batch=%s imgsz=%s",
			epochs,
			batch,
			self.config.imgsz,
		)
		results = model.train(
			data=str(data_yaml_path),
			epochs=epochs,
			batch=batch,
			imgsz=self.config.imgsz,
			lr0=lr0,
			optimizer=optimizer,
			augment=augment,
			patience=patience,
			project=str(project) if project else None,
			name=name,
			device=self.config.device,
			**kwargs,
		)
		return results

	def predict(self, source: str | Path | list[str] | list[Path], **kwargs: Any):
		"""Run YOLO inference.

		Args:
			source: Image path, directory, or list of paths.
			**kwargs: Extra predict kwargs.

		Returns:
			Ultralytics prediction results.
		"""
		model = self._ensure_model()
		inference_args = {
			"imgsz": self.config.imgsz,
			"conf": self.config.conf_thres,
			"iou": self.config.iou_thres,
			"device": self.config.device,
			**self.config.extra_predict_args,
			**kwargs,
		}
		return model.predict(source=source, **inference_args)

	def validate(self, data_yaml: str | Path, split: str = "val", **kwargs: Any):
		"""Run YOLO evaluation/validation.

		Args:
			data_yaml: Dataset yaml path.
			split: Data split to validate.
			**kwargs: Additional validation parameters.

		Returns:
			Ultralytics validation results object.
		"""
		model = self._ensure_model()
		yaml_path = Path(data_yaml)
		if not yaml_path.exists():
			raise FileNotFoundError(f"Data YAML not found: {yaml_path}")
		return model.val(data=str(yaml_path), split=split, imgsz=self.config.imgsz, **kwargs)

