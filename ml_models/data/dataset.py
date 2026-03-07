"""Dataset abstractions for tabular fraud detection tasks."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

try:
	import torch
	from torch.utils.data import DataLoader, Dataset as TorchDataset
except ImportError:
	torch = None
	DataLoader = object
	TorchDataset = object

LOGGER = logging.getLogger(__name__)


class ClaimsTabularDataset(TorchDataset):
	"""PyTorch dataset for tabular fraud detection.

	Args:
		features: Feature matrix as dataframe or numpy array.
		labels: Target vector as series or numpy array.

	Raises:
		ImportError: If PyTorch is not installed.
		ValueError: If input lengths mismatch or data is empty.
	"""

	def __init__(
		self,
		features: pd.DataFrame | np.ndarray,
		labels: pd.Series | np.ndarray,
	) -> None:
		if torch is None:
			raise ImportError("PyTorch is required for ClaimsTabularDataset.")

		x = features.values if isinstance(features, pd.DataFrame) else np.asarray(features)
		y = labels.values if isinstance(labels, pd.Series) else np.asarray(labels)

		if x.size == 0 or y.size == 0:
			raise ValueError("Features and labels must be non-empty.")
		if len(x) != len(y):
			raise ValueError("Features and labels must have the same number of rows.")

		self.features = torch.tensor(x, dtype=torch.float32)
		self.labels = torch.tensor(y, dtype=torch.float32).view(-1, 1)
		LOGGER.info("Initialized ClaimsTabularDataset with %s rows", len(self.labels))

	def __len__(self) -> int:
		"""Return number of samples in dataset."""
		return int(self.labels.shape[0])

	def __getitem__(self, index: int):
		"""Return one sample and its label."""
		return self.features[index], self.labels[index]


def create_dataloader(
	dataset: ClaimsTabularDataset,
	batch_size: int = 32,
	shuffle: bool = True,
	num_workers: int = 0,
):
	"""Create a PyTorch DataLoader for tabular fraud data.

	Args:
		dataset: ClaimsTabularDataset instance.
		batch_size: Batch size.
		shuffle: Whether to shuffle samples each epoch.
		num_workers: Number of worker subprocesses.

	Returns:
		PyTorch DataLoader instance.

	Raises:
		ImportError: If PyTorch is not installed.
		ValueError: If batch_size is invalid.
	"""
	if torch is None:
		raise ImportError("PyTorch is required to create DataLoader.")
	if batch_size <= 0:
		raise ValueError("batch_size must be greater than 0.")

	return DataLoader(
		dataset,
		batch_size=batch_size,
		shuffle=shuffle,
		num_workers=num_workers,
	)

