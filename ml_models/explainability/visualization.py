"""Visualization helpers for SHAP explanations."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


def _load_plot_modules():
	try:
		plt = importlib.import_module("matplotlib.pyplot")
		plotly_go = importlib.import_module("plotly.graph_objects")
		plotly_px = importlib.import_module("plotly.express")
		return plt, plotly_go, plotly_px
	except Exception as exc:
		raise ImportError("matplotlib and plotly are required for explainability visualizations.") from exc


def _prepare_output_paths(output_path: str | Path, stem_suffix: str) -> tuple[Path, Path]:
	base = Path(output_path)
	base.parent.mkdir(parents=True, exist_ok=True)
	png_path = base.with_suffix(".png") if base.suffix else base.parent / f"{base.name}_{stem_suffix}.png"
	html_path = base.with_suffix(".html") if base.suffix else base.parent / f"{base.name}_{stem_suffix}.html"
	return png_path, html_path


def plot_force_plot(explanation: Any, features: pd.DataFrame | np.ndarray, output_path: str | Path) -> dict[str, str]:
	"""Create local force-style contribution plot (PNG + HTML)."""
	plt, go, _ = _load_plot_modules()

	shap_values = np.asarray(getattr(explanation, "shap_values", []), dtype=float).reshape(-1)
	feature_names = list(features.columns) if isinstance(features, pd.DataFrame) else [f"f{i}" for i in range(len(shap_values))]
	feature_values = (
		features.iloc[0].to_numpy(dtype=float) if isinstance(features, pd.DataFrame) else np.asarray(features).reshape(-1)
	)

	contribution_df = pd.DataFrame(
		{
			"feature": feature_names,
			"value": feature_values,
			"shap": shap_values,
		}
	).sort_values("shap", key=np.abs, ascending=False)

	png_path, html_path = _prepare_output_paths(output_path, "force")

	plt.figure(figsize=(12, 6))
	colors = ["#d62728" if value > 0 else "#1f77b4" for value in contribution_df["shap"]]
	plt.barh(contribution_df["feature"].head(20)[::-1], contribution_df["shap"].head(20)[::-1], color=colors[:20][::-1])
	plt.axvline(0, color="black", linewidth=1)
	plt.title("SHAP Force-style Contribution Plot")
	plt.xlabel("SHAP contribution")
	plt.tight_layout()
	plt.savefig(png_path)
	plt.close()

	fig = go.Figure(
		data=[
			go.Bar(
				x=contribution_df["shap"].head(30),
				y=contribution_df["feature"].head(30),
				orientation="h",
				marker_color=["#d62728" if value > 0 else "#1f77b4" for value in contribution_df["shap"].head(30)],
			)
		]
	)
	fig.update_layout(title="Interactive SHAP Force-style Plot", xaxis_title="SHAP contribution", yaxis_title="Feature")
	fig.write_html(str(html_path), include_plotlyjs="cdn")

	return {"png": str(png_path), "html": str(html_path)}


def plot_summary_plot(shap_values: np.ndarray, features: pd.DataFrame | np.ndarray, output_path: str | Path) -> dict[str, str]:
	"""Create global SHAP summary plot (PNG + HTML)."""
	plt, go, px = _load_plot_modules()

	shap_arr = np.asarray(shap_values, dtype=float)
	feature_names = list(features.columns) if isinstance(features, pd.DataFrame) else [f"f{i}" for i in range(shap_arr.shape[1])]
	mean_abs = np.mean(np.abs(shap_arr), axis=0)

	summary_df = pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs}).sort_values(
		"mean_abs_shap", ascending=False
	)

	png_path, html_path = _prepare_output_paths(output_path, "summary")

	plt.figure(figsize=(12, 6))
	plt.barh(summary_df["feature"].head(20)[::-1], summary_df["mean_abs_shap"].head(20)[::-1], color="#2ca02c")
	plt.title("Global SHAP Feature Importance")
	plt.xlabel("Mean |SHAP value|")
	plt.tight_layout()
	plt.savefig(png_path)
	plt.close()

	fig = px.bar(
		summary_df.head(30).sort_values("mean_abs_shap", ascending=True),
		x="mean_abs_shap",
		y="feature",
		orientation="h",
		title="Interactive Global SHAP Summary",
	)
	fig.write_html(str(html_path), include_plotlyjs="cdn")
	return {"png": str(png_path), "html": str(html_path)}


def plot_waterfall_plot(explanation: Any, features: pd.DataFrame | np.ndarray, output_path: str | Path) -> dict[str, str]:
	"""Create waterfall breakdown for a single claim prediction."""
	plt, go, _ = _load_plot_modules()
	shap_values = np.asarray(getattr(explanation, "shap_values", []), dtype=float).reshape(-1)
	base_value = float(getattr(explanation, "base_value", 0.0))
	prediction = float(getattr(explanation, "prediction", 0.0))
	feature_names = list(features.columns) if isinstance(features, pd.DataFrame) else [f"f{i}" for i in range(len(shap_values))]

	df = pd.DataFrame({"feature": feature_names, "shap": shap_values}).sort_values("shap", key=np.abs, ascending=False)
	top = df.head(15)

	png_path, html_path = _prepare_output_paths(output_path, "waterfall")

	plt.figure(figsize=(12, 6))
	cumulative = base_value
	for idx, (_, row) in enumerate(top.iterrows()):
		color = "#d62728" if row["shap"] > 0 else "#1f77b4"
		plt.bar(idx, row["shap"], bottom=cumulative, color=color)
		cumulative += row["shap"]
	plt.axhline(base_value, color="gray", linestyle="--", label="Base value")
	plt.axhline(prediction, color="black", linestyle="-", label="Prediction")
	plt.xticks(range(len(top)), top["feature"], rotation=45, ha="right")
	plt.title("SHAP Waterfall Plot")
	plt.ylabel("Model output contribution")
	plt.legend()
	plt.tight_layout()
	plt.savefig(png_path)
	plt.close()

	fig = go.Figure(
		data=[
			go.Waterfall(
				orientation="v",
				measure=["relative"] * len(top),
				x=top["feature"].tolist(),
				y=top["shap"].tolist(),
				connector={"line": {"color": "rgb(63, 63, 63)"}},
			)
		]
	)
	fig.update_layout(title="Interactive SHAP Waterfall")
	fig.write_html(str(html_path), include_plotlyjs="cdn")
	return {"png": str(png_path), "html": str(html_path)}


def plot_dependence_plot(
	feature_name: str,
	shap_values: np.ndarray,
	features: pd.DataFrame | np.ndarray,
	output_path: str | Path,
) -> dict[str, str]:
	"""Create dependence plot for one feature (PNG + HTML)."""
	plt, go, px = _load_plot_modules()

	if not isinstance(features, pd.DataFrame):
		feature_columns = [f"f{i}" for i in range(np.asarray(features).shape[1])]
		feature_df = pd.DataFrame(features, columns=feature_columns)
	else:
		feature_df = features.copy()

	if feature_name not in feature_df.columns:
		raise ValueError(f"Feature '{feature_name}' not found in feature columns.")

	feature_idx = list(feature_df.columns).index(feature_name)
	shap_arr = np.asarray(shap_values, dtype=float)
	feature_shap = shap_arr[:, feature_idx]
	feature_vals = feature_df[feature_name].to_numpy()

	png_path, html_path = _prepare_output_paths(output_path, f"dependence_{feature_name}")

	plt.figure(figsize=(10, 6))
	plt.scatter(feature_vals, feature_shap, alpha=0.6, s=25)
	plt.title(f"SHAP Dependence Plot: {feature_name}")
	plt.xlabel(feature_name)
	plt.ylabel("SHAP value")
	plt.tight_layout()
	plt.savefig(png_path)
	plt.close()

	dep_df = pd.DataFrame({feature_name: feature_vals, "shap_value": feature_shap})
	fig = px.scatter(dep_df, x=feature_name, y="shap_value", title=f"Interactive Dependence: {feature_name}")
	fig.write_html(str(html_path), include_plotlyjs="cdn")
	return {"png": str(png_path), "html": str(html_path)}

