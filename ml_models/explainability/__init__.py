"""Explainability package exports."""

from .batch_explainer import BatchShapExplainer
from .explainability_api import router as explainability_router
from .feature_mapper import FeatureMapper
from .report_integration import (
	extract_top_contributors,
	format_explanation_for_llm,
	generate_natural_language_explanation,
)
from .shap_explainer import GlobalExplanation, LocalExplanation, ShapExplainerEngine
from .visualization import (
	plot_dependence_plot,
	plot_force_plot,
	plot_summary_plot,
	plot_waterfall_plot,
)

__all__ = [
	"BatchShapExplainer",
	"FeatureMapper",
	"GlobalExplanation",
	"LocalExplanation",
	"ShapExplainerEngine",
	"explainability_router",
	"extract_top_contributors",
	"format_explanation_for_llm",
	"generate_natural_language_explanation",
	"plot_dependence_plot",
	"plot_force_plot",
	"plot_summary_plot",
	"plot_waterfall_plot",
]

