"""FastAPI endpoints for serving SHAP explanations."""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml_models.ensemble.weighted_ensemble import WeightedEnsembleFraudModel

from .batch_explainer import BatchShapExplainer
from .feature_mapper import FeatureMapper
from .report_integration import extract_top_contributors, format_explanation_for_llm
from .shap_explainer import ShapExplainerEngine
from .visualization import (
    plot_dependence_plot,
    plot_force_plot,
    plot_summary_plot,
    plot_waterfall_plot,
)

LOGGER = logging.getLogger(__name__)

_fastapi = importlib.import_module("fastapi")
_pydantic = importlib.import_module("pydantic")

APIRouter = getattr(_fastapi, "APIRouter")
HTTPException = getattr(_fastapi, "HTTPException")
BaseModel = getattr(_pydantic, "BaseModel")
Field = getattr(_pydantic, "Field")

router = APIRouter(prefix="/explain", tags=["explainability"])


class BatchExplainRequest(BaseModel):
    """Batch explanation request payload."""

    claims: list[dict[str, Any]] = Field(default_factory=list)
    feature_names: list[str] = Field(default_factory=list)


def _default_paths() -> dict[str, Path]:
    package_root = Path(__file__).resolve().parents[1]
    return {
        "ensemble_model": package_root / "models" / "ensemble" / "ensemble.pkl",
        "claims_data": package_root / "data" / "test" / "test_processed.csv",
        "plots_dir": package_root / "explainability" / "outputs",
    }


def _init_explainer_engine(feature_names: list[str], background_data: np.ndarray) -> tuple[WeightedEnsembleFraudModel, BatchShapExplainer]:
    paths = _default_paths()
    ensemble = WeightedEnsembleFraudModel.load_model(paths["ensemble_model"])

    model = ensemble.rf_model.model
    explainer = ShapExplainerEngine(
        model=model,
        model_type="random_forest",
        feature_names=feature_names,
        background_data=background_data,
        predict_proba_fn=lambda x: ensemble.predict_proba(x)[:, 1],
        feature_mapper=FeatureMapper(feature_names=feature_names),
    )
    batch_explainer = BatchShapExplainer(explainer)
    return ensemble, batch_explainer


@router.get("/{claim_id}")
def explain_claim(claim_id: int) -> dict[str, Any]:
    """Return SHAP explanation, plots, and NL rationale for one claim."""
    paths = _default_paths()
    data_path = paths["claims_data"]
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Claims data not found: {data_path}")

    df = pd.read_csv(data_path)
    if claim_id < 0 or claim_id >= len(df):
        raise HTTPException(status_code=404, detail=f"claim_id {claim_id} out of range.")

    feature_names = [col for col in df.columns if col != "fraud_label"]
    x = df[feature_names].to_numpy()
    x_row = x[claim_id]

    try:
        ensemble, batch_explainer = _init_explainer_engine(feature_names=feature_names, background_data=x)
        prediction = float(ensemble.predict_proba(x_row.reshape(1, -1))[:, 1][0])
        local_exp = batch_explainer.explainer_engine.explain_local(x_row, prediction=prediction)
        global_exp = batch_explainer.explain_global_cached(x)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {exc}")

    plots_dir = paths["plots_dir"] / f"claim_{claim_id}"
    plots_dir.mkdir(parents=True, exist_ok=True)

    features_df = pd.DataFrame([x_row], columns=feature_names)
    force_paths = plot_force_plot(local_exp, features_df, plots_dir / "force_plot")
    waterfall_paths = plot_waterfall_plot(local_exp, features_df, plots_dir / "waterfall_plot")
    summary_paths = plot_summary_plot(global_exp.shap_values, pd.DataFrame(x, columns=feature_names), plots_dir / "summary_plot")
    dependence_paths = plot_dependence_plot(
        feature_name=feature_names[0],
        shap_values=global_exp.shap_values,
        features=pd.DataFrame(x, columns=feature_names),
        output_path=plots_dir / "dependence_plot",
    )

    top_features = extract_top_contributors(local_exp.mapped_feature_contributions, top_k=5)
    report_payload = format_explanation_for_llm(
        claim_id=str(claim_id),
        fraud_probability=prediction,
        top_features=top_features,
        yolo_output={"affected_parts": [], "count_by_damage_type": {}, "severity_score": 0.0},
        claim_context={},
    )

    return {
        "claim_id": claim_id,
        "fraud_probability": prediction,
        "local_explanation": {
            "base_value": local_exp.base_value,
            "prediction": local_exp.prediction,
            "mapped_feature_contributions": local_exp.mapped_feature_contributions,
            "elapsed_seconds": local_exp.elapsed_seconds,
        },
        "global_top_features": global_exp.feature_importance.head(20).to_dict(orient="records"),
        "plots": {
            "force_plot": force_paths,
            "waterfall_plot": waterfall_paths,
            "summary_plot": summary_paths,
            "dependence_plot": dependence_paths,
        },
        "llm_report_payload": report_payload,
    }


@router.post("/batch")
def explain_batch(request: BatchExplainRequest) -> dict[str, Any]:
    """Generate batch SHAP explanations for multiple claims."""
    if not request.claims:
        raise HTTPException(status_code=400, detail="claims payload cannot be empty.")

    claims_df = pd.DataFrame(request.claims)
    feature_names = request.feature_names or claims_df.columns.tolist()
    missing = [name for name in feature_names if name not in claims_df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required feature columns: {missing}")

    x = claims_df[feature_names].to_numpy()

    try:
        ensemble, batch_explainer = _init_explainer_engine(feature_names=feature_names, background_data=x)
        predictions = ensemble.predict_proba(x)[:, 1]
        local_payload = batch_explainer.explain(x_data=x, explanation_type="local", predictions=predictions)
        global_payload = batch_explainer.explain(x_data=x, explanation_type="global")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Batch explanation failed: {exc}")

    return {
        "count": len(request.claims),
        "local_explanations": local_payload,
        "global_explanation": global_payload,
    }
