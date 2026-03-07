"""Train tabular weighted-ensemble fraud model from auto_claims.csv."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from ml_models.data.data_loader import load_raw_data
from ml_models.data.preprocessing import preprocess_and_split
from ml_models.ensemble.train import train_ensemble_engine


LOGGER = logging.getLogger(__name__)


def _configure_logging() -> None:
	if not logging.getLogger().handlers:
		logging.basicConfig(
			level=logging.INFO,
			format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
		)


def run_training(
	raw_csv: str | Path,
	output_model: str | Path,
	report_root: str | Path | None = None,
	test_size: float = 0.15,
	val_size: float = 0.15,
) -> dict[str, Any]:
	"""Run full preprocessing + weighted ensemble training pipeline."""
	_configure_logging()
	package_root = Path(__file__).resolve().parents[1]

	raw_csv_path = Path(raw_csv)
	output_model_path = Path(output_model)
	model_root = output_model_path.parent
	resolved_report_root = Path(report_root) if report_root else package_root / "evaluation" / "reports"

	data_root = package_root / "data"
	preprocessors_dir = package_root / "models" / "preprocessors"

	LOGGER.info("Loading tabular data from %s", raw_csv_path)
	dataframe = load_raw_data(raw_csv_path)

	LOGGER.info("Preprocessing tabular dataset and creating train/val/test splits")
	preprocess_and_split(
		dataframe=dataframe,
		target_column="fraud_label",
		data_root=data_root,
		artifacts_dir=preprocessors_dir,
		test_size=test_size,
		val_size=val_size,
		save_outputs=True,
	)

	LOGGER.info("Training weighted ensemble fraud model")
	summary = train_ensemble_engine(
		data_root=data_root,
		model_root=model_root,
		report_root=resolved_report_root,
		target_column="fraud_label",
		apply_rus=True,
		tune_models=True,
		cv_folds=5,
	)

	artifacts = summary.get("artifacts", {})
	trained_path = artifacts.get("ensemble")
	if not trained_path:
		raise RuntimeError("Training finished but ensemble artifact path is missing from summary.")

	if Path(trained_path).resolve() != output_model_path.resolve():
		raise RuntimeError(
			f"Expected ensemble model at {output_model_path}, but training produced {trained_path}"
		)

	summary_path = resolved_report_root / "train_ensemble_script_summary.json"
	summary_path.parent.mkdir(parents=True, exist_ok=True)
	summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
	LOGGER.info("Saved script summary to %s", summary_path)
	return summary


def build_arg_parser() -> argparse.ArgumentParser:
	package_root = Path(__file__).resolve().parents[1]
	parser = argparse.ArgumentParser(description="Train weighted ensemble fraud model.")
	parser.add_argument(
		"--raw-csv",
		type=str,
		default=str(package_root / "data" / "raw" / "auto_claims.csv"),
		help="Path to tabular CSV (auto_claims.csv).",
	)
	parser.add_argument(
		"--output-model",
		type=str,
		default=str(package_root / "models" / "ensemble" / "ensemble.pkl"),
		help="Output path for ensemble model artifact.",
	)
	parser.add_argument(
		"--report-root",
		type=str,
		default=str(package_root / "evaluation" / "reports"),
		help="Directory to save training reports.",
	)
	parser.add_argument("--test-size", type=float, default=0.15, help="Test split ratio.")
	parser.add_argument("--val-size", type=float, default=0.15, help="Validation split ratio.")
	return parser


if __name__ == "__main__":
	args = build_arg_parser().parse_args()
	run_training(
		raw_csv=args.raw_csv,
		output_model=args.output_model,
		report_root=args.report_root,
		test_size=args.test_size,
		val_size=args.val_size,
	)
