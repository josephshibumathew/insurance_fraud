"""Data quality checks and validation utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)


def impute_missing_values(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Impute missing values using median/mode strategy.

    Args:
        dataframe: Input dataframe with missing values.

    Returns:
        Tuple of imputed dataframe and imputation summary.
    """
    df = dataframe.copy()
    numerical_columns = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_columns = [col for col in df.columns if col not in numerical_columns]

    summary: dict[str, Any] = {"numerical": {}, "categorical": {}}

    for column in numerical_columns:
        median_value = df[column].median()
        missing_count = int(df[column].isna().sum())
        df[column] = df[column].fillna(median_value)
        summary["numerical"][column] = {
            "imputation": "median",
            "value": float(median_value) if pd.notna(median_value) else None,
            "missing_filled": missing_count,
        }

    for column in categorical_columns:
        mode_series = df[column].mode(dropna=True)
        mode_value = mode_series.iloc[0] if not mode_series.empty else "unknown"
        missing_count = int(df[column].isna().sum())
        df[column] = df[column].fillna(mode_value)
        summary["categorical"][column] = {
            "imputation": "mode",
            "value": str(mode_value),
            "missing_filled": missing_count,
        }

    LOGGER.info("Completed missing value imputation.")
    return df, summary


def detect_outliers_iqr(
    dataframe: pd.DataFrame,
    iqr_multiplier: float = 1.5,
) -> dict[str, dict[str, Any]]:
    """Detect outliers in numerical columns using IQR.

    Args:
        dataframe: Input dataframe.
        iqr_multiplier: IQR multiplier for upper/lower bounds.

    Returns:
        Outlier summary per numerical column.
    """
    outlier_summary: dict[str, dict[str, Any]] = {}
    numeric_columns = dataframe.select_dtypes(include=["number"]).columns.tolist()

    for column in numeric_columns:
        q1 = dataframe[column].quantile(0.25)
        q3 = dataframe[column].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - iqr_multiplier * iqr
        upper = q3 + iqr_multiplier * iqr

        mask = (dataframe[column] < lower) | (dataframe[column] > upper)
        indices = dataframe.index[mask].tolist()

        outlier_summary[column] = {
            "count": int(mask.sum()),
            "lower_bound": float(lower) if pd.notna(lower) else None,
            "upper_bound": float(upper) if pd.notna(upper) else None,
            "indices": [int(i) for i in indices],
        }

    return outlier_summary


def validate_schema(
    dataframe: pd.DataFrame,
    expected_schema: dict[str, str],
) -> list[str]:
    """Validate data types against expected schema.

    Args:
        dataframe: Input dataframe.
        expected_schema: Map from column to logical dtype class.

    Returns:
        List of schema mismatch errors.
    """
    errors: list[str] = []

    for column, expected_type in expected_schema.items():
        if column not in dataframe.columns:
            errors.append(f"Missing expected column: {column}")
            continue

        series = dataframe[column]
        if expected_type == "numeric" and not pd.api.types.is_numeric_dtype(series):
            errors.append(f"Column '{column}' expected numeric but got {series.dtype}")
        elif expected_type == "categorical" and pd.api.types.is_numeric_dtype(series):
            errors.append(f"Column '{column}' expected categorical but got {series.dtype}")
        elif expected_type == "binary":
            unique_values = set(pd.Series(series).dropna().unique().tolist())
            if not unique_values.issubset({0, 1}):
                errors.append(
                    f"Column '{column}' expected binary values {{0,1}} but got {sorted(unique_values)}"
                )

    return errors


def generate_data_quality_report(
    dataframe: pd.DataFrame,
    expected_schema: dict[str, str],
    report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Generate a data quality report with imputation, schema, and outlier details.

    Args:
        dataframe: Input dataframe.
        expected_schema: Expected schema mapping for validation.
        report_path: Optional path to save report JSON.

    Returns:
        Data quality report dictionary.
    """
    missing_before = dataframe.isna().sum().to_dict()
    imputed_df, imputation_summary = impute_missing_values(dataframe)
    missing_after = imputed_df.isna().sum().to_dict()

    schema_errors = validate_schema(imputed_df, expected_schema=expected_schema)
    outlier_summary = detect_outliers_iqr(imputed_df)

    report: dict[str, Any] = {
        "row_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "missing_values_before": {k: int(v) for k, v in missing_before.items()},
        "missing_values_after": {k: int(v) for k, v in missing_after.items()},
        "imputation_summary": imputation_summary,
        "schema_errors": schema_errors,
        "outliers": outlier_summary,
    }

    if "fraud_label" in imputed_df.columns:
        report["fraud_distribution"] = (
            imputed_df["fraud_label"].value_counts(dropna=False).to_dict()
        )

    if report_path:
        output = Path(report_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as fp:
            json.dump(report, fp, indent=2)
        LOGGER.info("Data quality report saved to %s", output)

    return report
