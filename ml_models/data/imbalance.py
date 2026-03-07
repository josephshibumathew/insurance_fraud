"""Imbalance handling utilities using random undersampling."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from imblearn.under_sampling import RandomUnderSampler

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SamplingStats:
	"""Sampling summary for auditability.

	Attributes:
		before_counts: Class counts before undersampling.
		after_counts: Class counts after undersampling.
		sampled_rows: Number of rows retained after undersampling.
	"""

	before_counts: dict[int, int]
	after_counts: dict[int, int]
	sampled_rows: int


def random_undersample_train(
	x_train: pd.DataFrame,
	y_train: pd.Series,
	random_state: int = 42,
) -> tuple[pd.DataFrame, pd.Series, SamplingStats]:
	"""Apply random undersampling to balance binary fraud labels.

	Args:
		x_train: Training feature matrix.
		y_train: Training labels.
		random_state: Random seed for reproducibility.

	Returns:
		Tuple of balanced features, labels, and sampling statistics.

	Raises:
		ValueError: If labels are not binary or balancing fails.
	"""
	if x_train.empty or y_train.empty:
		raise ValueError("x_train and y_train must be non-empty.")

	y_series = y_train.reset_index(drop=True)
	x_frame = x_train.reset_index(drop=True)

	unique_labels = set(pd.Series(y_series).dropna().unique().tolist())
	if unique_labels != {0, 1}:
		raise ValueError(f"Expected binary labels {{0,1}} but found: {sorted(unique_labels)}")

	before_counts = pd.Series(y_series).value_counts().sort_index().to_dict()
	LOGGER.info("Class distribution before RUS: %s", before_counts)

	sampler = RandomUnderSampler(
		sampling_strategy=1.0,
		replacement=False,
		random_state=random_state,
	)
	x_balanced, y_balanced = sampler.fit_resample(x_frame, y_series)

	x_balanced_df = pd.DataFrame(x_balanced, columns=x_frame.columns)
	y_balanced_series = pd.Series(y_balanced, name=y_train.name or "fraud_label")

	after_counts = y_balanced_series.value_counts().sort_index().to_dict()
	if after_counts.get(0) != after_counts.get(1):
		raise ValueError("Undersampling did not produce a 50/50 class balance.")

	sample_indices = np.asarray(getattr(sampler, "sample_indices_", []))
	if sample_indices.size > 0:
		majority_label = 0 if before_counts[0] > before_counts[1] else 1
		majority_sample_indices = sample_indices[y_series.iloc[sample_indices].to_numpy() == majority_label]
		if len(majority_sample_indices) != len(np.unique(majority_sample_indices)):
			raise ValueError("Duplicate majority-class samples detected after undersampling.")

	stats = SamplingStats(
		before_counts={int(k): int(v) for k, v in before_counts.items()},
		after_counts={int(k): int(v) for k, v in after_counts.items()},
		sampled_rows=int(len(y_balanced_series)),
	)
	LOGGER.info("Class distribution after RUS: %s", stats.after_counts)
	return x_balanced_df, y_balanced_series, stats

