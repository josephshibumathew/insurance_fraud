"""End-to-end multimodal inference for fraud scoring."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml_models.ensemble.weighted_ensemble import WeightedEnsembleFraudModel
from ml_models.multimodal.feature_extraction import extract_batch_image_features, extract_image_features
from ml_models.multimodal.fusion_model import MultiModalFusionModel
from ml_models.yolo_module.inference import process_batch_images, process_single_image
from ml_models.yolo_module.yolo_model import YOLOConfig, YOLOModelWrapper

LOGGER = logging.getLogger(__name__)


class MultiModalInferenceEngine:
	"""Inference engine that combines structured + visual fraud evidence."""

	def __init__(
		self,
		ensemble_model_path: str | Path,
		yolo_weights_path: str | Path,
		fusion_model_path: str | Path,
	) -> None:
		self.ensemble_model = WeightedEnsembleFraudModel.load_model(ensemble_model_path)
		self.yolo_model = YOLOModelWrapper(
			weights_path=str(yolo_weights_path),
			config=YOLOConfig(imgsz=640, conf_thres=0.25, iou_thres=0.45),
		)
		self.fusion_model = MultiModalFusionModel.load(fusion_model_path)

	def process_single_claim(
		self,
		structured_features: pd.DataFrame | np.ndarray,
		image_path: str | Path,
		claim_description: str | None = None,
	) -> dict[str, Any]:
		"""Process a single claim and return final fraud score with explainability."""
		if isinstance(structured_features, pd.DataFrame):
			x_struct = structured_features
		else:
			x_struct = np.asarray(structured_features)
			if x_struct.ndim == 1:
				x_struct = x_struct.reshape(1, -1)

		structured_proba = self.ensemble_model.predict_proba(x_struct)[:, 1]
		yolo_output = process_single_image(self.yolo_model, image_path=image_path)
		image_bundle = extract_image_features(yolo_output, claim_description=claim_description)
		image_matrix = image_bundle.feature_vector.reshape(1, -1)

		final_proba = float(
			self.fusion_model.predict_proba(
				ensemble_proba=structured_proba,
				image_features=image_matrix,
			)[0]
		)

		output = {
			"final_fraud_probability": final_proba,
			"final_fraud_prediction": int(final_proba >= 0.5),
			"confidence": float(abs(final_proba - 0.5) * 2),
			"intermediate_outputs": {
				"structured_probability": float(structured_proba[0]),
				"image_features": {
					"feature_names": image_bundle.feature_names,
					"feature_vector": image_bundle.feature_vector.tolist(),
				},
				"yolo_output": yolo_output,
			},
		}
		return output

	def process_batch_claims(
		self,
		structured_features: pd.DataFrame | np.ndarray,
		image_paths: list[str | Path],
		claim_descriptions: list[str] | None = None,
	) -> dict[str, Any]:
		"""Batch process multiple claims and return multimodal fraud scores."""
		x_struct = structured_features.values if isinstance(structured_features, pd.DataFrame) else np.asarray(structured_features)
		if x_struct.shape[0] != len(image_paths):
			raise ValueError("structured_features rows must match number of image_paths.")

		structured_proba = self.ensemble_model.predict_proba(x_struct)[:, 1]

		batch_yolo = process_batch_images(
			model_wrapper=self.yolo_model,
			image_paths=image_paths,
			conf_threshold=0.25,
		)
		item_outputs = batch_yolo["items"]
		if len(item_outputs) != len(image_paths):
			raise ValueError("Mismatch between processed YOLO outputs and requested image paths.")

		image_matrix, feature_names, metadata_list = extract_batch_image_features(
			yolo_outputs=item_outputs,
			claim_descriptions=claim_descriptions,
		)

		final_proba = self.fusion_model.predict_proba(
			ensemble_proba=structured_proba,
			image_features=image_matrix,
		)

		items: list[dict[str, Any]] = []
		for index, probability in enumerate(final_proba):
			items.append(
				{
					"claim_index": index,
					"final_fraud_probability": float(probability),
					"final_fraud_prediction": int(probability >= 0.5),
					"confidence": float(abs(probability - 0.5) * 2),
					"intermediate_outputs": {
						"structured_probability": float(structured_proba[index]),
						"image_features": {
							"feature_names": feature_names,
							"feature_vector": image_matrix[index].tolist(),
						},
						"yolo_output": item_outputs[index],
						"metadata": metadata_list[index],
					},
				}
			)

		return {
			"items": items,
			"batch_summary": {
				"claims": len(items),
				"average_fraud_probability": float(np.mean(final_proba)),
			},
		}

