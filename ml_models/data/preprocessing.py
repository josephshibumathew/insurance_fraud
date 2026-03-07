"""Preprocessing utilities for tabular fraud detection data."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler

LOGGER = logging.getLogger(__name__)


def separate_features_target(
	dataframe: pd.DataFrame,
	target_column: str = "fraud_label",
) -> tuple[pd.DataFrame, pd.Series]:
	"""Split dataframe into features and target.

	Args:
		dataframe: Input dataframe containing all features and target.
		target_column: Name of the target label column.

	Returns:
		Tuple of features dataframe and target series.

	Raises:
		ValueError: If target column is missing or dataframe is empty.
	"""
	if dataframe.empty:
		raise ValueError("Input dataframe is empty.")
	if target_column not in dataframe.columns:
		raise ValueError(f"Target column '{target_column}' not found in dataframe.")

	x = dataframe.drop(columns=[target_column]).copy()
	y = dataframe[target_column].copy()
	return x, y


def _build_preprocessor(
	x_train: pd.DataFrame,
	scaler_type: str = "standard",
) -> ColumnTransformer:
	"""Build a column transformer for categorical and numerical preprocessing.

	Args:
		x_train: Training feature set.
		scaler_type: Numerical scaler type, either 'standard' or 'minmax'.

	Returns:
		Configured column transformer.

	Raises:
		ValueError: If unsupported scaler type is provided.
	"""
	if scaler_type not in {"standard", "minmax"}:
		raise ValueError("scaler_type must be either 'standard' or 'minmax'.")

	categorical_columns = x_train.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
	numerical_columns = x_train.select_dtypes(include=["number"]).columns.tolist()

	scaler = StandardScaler() if scaler_type == "standard" else MinMaxScaler()

	try:
		encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
	except TypeError:
		encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)

	categorical_pipeline = Pipeline(
		steps=[
			("imputer", SimpleImputer(strategy="most_frequent")),
			("onehot", encoder)
		]
	)
	numerical_pipeline = Pipeline(
		steps=[
			("imputer", SimpleImputer(strategy="median")),
			("scaler", scaler),
		]
	)

	preprocessor = ColumnTransformer(
		transformers=[
			("categorical", categorical_pipeline, categorical_columns),
			("numerical", numerical_pipeline, numerical_columns),
		],
		remainder="drop",
	)
	return preprocessor


def _ensure_directories(base_data_dir: Path, artifacts_dir: Path) -> None:
	"""Create output directories if needed.

	Args:
		base_data_dir: Data root directory.
		artifacts_dir: Directory for preprocessor artifacts.
	"""
	for split in ("train", "val", "test", "processed"):
		(base_data_dir / split).mkdir(parents=True, exist_ok=True)
	artifacts_dir.mkdir(parents=True, exist_ok=True)


def preprocess_and_split(
	dataframe: pd.DataFrame,
	target_column: str = "fraud_label",
	scaler_type: str = "standard",
	random_state: int = 42,
	test_size: float = 0.15,
	val_size: float = 0.15,
	data_root: str | Path | None = None,
	artifacts_dir: str | Path | None = None,
	save_outputs: bool = True,
) -> dict[str, Any]:
	"""Run full tabular preprocessing and stratified data splitting.

	Args:
		dataframe: Input raw dataframe.
		target_column: Name of target label column.
		scaler_type: Scaling strategy for numeric columns.
		random_state: Seed for reproducibility.
		test_size: Proportion of data reserved for test set.
		val_size: Proportion of data reserved for validation set.
		data_root: Root path for data split outputs.
		artifacts_dir: Output path for preprocessing artifacts.
		save_outputs: Whether to save transformed splits and artifacts.

	Returns:
		Dictionary containing transformed train/val/test data and metadata.

	Raises:
		ValueError: If split ratios are invalid.
	"""
	if not (0 < test_size < 1 and 0 < val_size < 1 and (test_size + val_size) < 1):
		raise ValueError("Invalid split ratios. Ensure 0 < test_size + val_size < 1.")

	x, y = separate_features_target(dataframe, target_column=target_column)

	x_train_val, x_test, y_train_val, y_test = train_test_split(
		x,
		y,
		test_size=test_size,
		stratify=y,
		random_state=random_state,
	)

	val_relative_size = val_size / (1 - test_size)
	x_train, x_val, y_train, y_val = train_test_split(
		x_train_val,
		y_train_val,
		test_size=val_relative_size,
		stratify=y_train_val,
		random_state=random_state,
	)

	preprocessor = _build_preprocessor(x_train=x_train, scaler_type=scaler_type)
	x_train_t = preprocessor.fit_transform(x_train)
	x_val_t = preprocessor.transform(x_val)
	x_test_t = preprocessor.transform(x_test)

	feature_names = preprocessor.get_feature_names_out().tolist()
	x_train_df = pd.DataFrame(x_train_t, columns=feature_names, index=x_train.index)
	x_val_df = pd.DataFrame(x_val_t, columns=feature_names, index=x_val.index)
	x_test_df = pd.DataFrame(x_test_t, columns=feature_names, index=x_test.index)

	package_root = Path(__file__).resolve().parents[1]
	resolved_data_root = Path(data_root) if data_root else Path(__file__).resolve().parent
	resolved_artifacts_dir = (
		Path(artifacts_dir)
		if artifacts_dir
		else package_root / "models" / "preprocessors"
	)

	if save_outputs:
		_ensure_directories(base_data_dir=resolved_data_root, artifacts_dir=resolved_artifacts_dir)

		train_out = pd.concat(
			[x_train_df.reset_index(drop=True), y_train.reset_index(drop=True)],
			axis=1,
		)
		val_out = pd.concat(
			[x_val_df.reset_index(drop=True), y_val.reset_index(drop=True)],
			axis=1,
		)
		test_out = pd.concat(
			[x_test_df.reset_index(drop=True), y_test.reset_index(drop=True)],
			axis=1,
		)

		train_out.to_csv(resolved_data_root / "train" / "train_processed.csv", index=False)
		val_out.to_csv(resolved_data_root / "val" / "val_processed.csv", index=False)
		test_out.to_csv(resolved_data_root / "test" / "test_processed.csv", index=False)
		train_out.to_csv(resolved_data_root / "processed" / "all_train_processed.csv", index=False)

		joblib.dump(preprocessor, resolved_artifacts_dir / "preprocessor.joblib")
		metadata = {
			"target_column": target_column,
			"scaler_type": scaler_type,
			"feature_names": feature_names,
			"train_rows": len(x_train_df),
			"val_rows": len(x_val_df),
			"test_rows": len(x_test_df),
		}
		with (resolved_artifacts_dir / "preprocessing_metadata.json").open("w", encoding="utf-8") as fp:
			json.dump(metadata, fp, indent=2)

		LOGGER.info("Saved preprocessing artifacts to %s", resolved_artifacts_dir)

	LOGGER.info(
		"Split sizes -> train: %s, val: %s, test: %s",
		len(x_train_df),
		len(x_val_df),
		len(x_test_df),
	)

	return {
		"X_train": x_train_df,
		"X_val": x_val_df,
		"X_test": x_test_df,
		"y_train": y_train.reset_index(drop=True),
		"y_val": y_val.reset_index(drop=True),
		"y_test": y_test.reset_index(drop=True),
		"feature_names": feature_names,
		"preprocessor": preprocessor,
	}

