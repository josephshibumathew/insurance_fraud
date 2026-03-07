"""Data loading utilities for automobile insurance fraud detection."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import pandas as pd

LOGGER = logging.getLogger(__name__)

DEFAULT_EXPECTED_COLUMNS: tuple[str, ...] = (
    "policy_type",
    "claim_amount",
    "accident_location",
    "vehicle_age",
    "driver_age",
    "previous_claims",
    "fraud_label",
)

NUMERIC_COLUMNS: tuple[str, ...] = (
    "claim_amount",
    "vehicle_age",
    "driver_age",
    "previous_claims",
)

SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

AUTO_CLAIMS_SIGNATURE_COLUMNS: tuple[str, ...] = (
    "PolicyType",
    "AccidentArea",
    "Age",
    "FraudFound",
)

AUTO_CLAIMS_RENAME_MAP: dict[str, str] = {
    "FraudFound": "fraud_label",
    "PolicyType": "policy_type",
    "AccidentArea": "accident_location",
    "Age": "driver_age",
    "PastNumberOfClaims": "previous_claims",
}


def _normalize_fraud_label(series: pd.Series) -> pd.Series:
    """Normalize fraud labels to binary values.

    Args:
        series: Input fraud label series.

    Returns:
        A binary series with values in {0, 1}.

    Raises:
        ValueError: If unsupported fraud label values are found.
    """
    if pd.api.types.is_numeric_dtype(series):
        normalized = series.astype("Int64")
        unique_values = set(normalized.dropna().unique().tolist())
        if not unique_values.issubset({0, 1}):
            raise ValueError("Numeric fraud_label must contain only 0/1 values.")
        return normalized.astype(int)

    mapping = {
        "y": 1,
        "yes": 1,
        "true": 1,
        "fraud": 1,
        "1": 1,
        "n": 0,
        "no": 0,
        "false": 0,
        "legit": 0,
        "0": 0,
    }
    lowered = series.astype(str).str.strip().str.lower()
    normalized = lowered.map(mapping)
    if normalized.isna().any():
        invalid_values = sorted(lowered[normalized.isna()].unique().tolist())
        raise ValueError(
            "Unsupported fraud_label values found: "
            f"{invalid_values[:10]}"
        )
    return normalized.astype(int)


def load_raw_data(
    filepath: str | Path,
    expected_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Load and validate raw CSV data.

    Args:
        filepath: Path to the raw CSV dataset.
        expected_columns: Required columns that must exist in the data.

    Returns:
        Parsed and validated dataframe.

    Raises:
        FileNotFoundError: If the provided file path does not exist.
        ValueError: If data is empty, corrupt, or missing required columns.
    """
    path = Path(filepath)
    required = tuple(expected_columns) if expected_columns is not None else DEFAULT_EXPECTED_COLUMNS

    LOGGER.info("Loading raw dataset from: %s", path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    try:
        df = pd.read_csv(path, low_memory=False)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"Dataset is empty: {path}") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"Dataset appears corrupt or malformed: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Dataset encoding issue detected while reading: {path}"
        ) from exc

    if df.empty:
        raise ValueError(f"Dataset has no rows: {path}")

    original_columns = set(df.columns)
    if "FraudFound" in df.columns and "fraud_label" not in df.columns:
        df = df.rename(columns=AUTO_CLAIMS_RENAME_MAP)

    missing_cols = [col for col in required if col not in df.columns]
    if missing_cols and expected_columns is None:
        is_auto_claims_dataset = set(AUTO_CLAIMS_SIGNATURE_COLUMNS).issubset(original_columns)
        if not is_auto_claims_dataset:
            raise ValueError(f"Missing required columns: {missing_cols}")
    elif missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "fraud_label" in df.columns:
        df["fraud_label"] = _normalize_fraud_label(df["fraud_label"])

    LOGGER.info("Loaded dataset shape: rows=%s cols=%s", df.shape[0], df.shape[1])
    if "fraud_label" in df.columns:
        LOGGER.info(
            "Fraud label distribution: %s",
            df["fraud_label"].value_counts(dropna=False).to_dict(),
        )
    return df


def load_image_manifest(images_root: str | Path) -> pd.DataFrame:
    """Build an image manifest from training/validation claim folders.

    Expected layout:
      images_root/
        training/claim_000/*.jpg
        training/claim_001/*.jpg
        validation/claim_000/*.jpg
        validation/claim_001/*.jpg

    Args:
        images_root: Root directory that contains training/validation subfolders.

    Returns:
        DataFrame with columns:
        split, claim_folder, fraud_label, image_name, image_path
    """
    root = Path(images_root)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Images root directory not found: {root}")

    rows: list[dict[str, str | int]] = []
    for split in ("training", "validation"):
        split_dir = root / split
        if not split_dir.exists():
            continue

        for claim_dir in sorted([path for path in split_dir.iterdir() if path.is_dir()]):
            label = 1 if claim_dir.name.endswith("001") else 0 if claim_dir.name.endswith("000") else -1
            for image_path in sorted(claim_dir.rglob("*")):
                if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                    continue
                rows.append(
                    {
                        "split": split,
                        "claim_folder": claim_dir.name,
                        "fraud_label": label,
                        "image_name": image_path.name,
                        "image_path": str(image_path),
                    }
                )

    if not rows:
        raise ValueError(f"No supported images found under: {root}")

    manifest = pd.DataFrame(rows)
    LOGGER.info(
        "Loaded image manifest with %s images from %s",
        len(manifest),
        root,
    )
    return manifest
