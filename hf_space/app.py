"""
Hugging Face Space — ML Inference API
Serves fraud scoring (ensemble) and damage detection (YOLOv11) endpoints.

Expected layout inside the Space repo:
  app.py
  ml_models/           ← copy from main repo's ml_models/
  models/
    ensemble.pkl
    preprocessor.joblib
    individual/
      xgb_model.joblib
    yolo/
      best.pt
"""

from __future__ import annotations

import io
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Ensure ml_models package is importable ─────────────────────────────
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml-api")

# ── Model paths ────────────────────────────────────────────────────────
MODELS_DIR = ROOT / "models"
ENSEMBLE_PATH = MODELS_DIR / "ensemble.pkl"
PREPROCESSOR_PATH = MODELS_DIR / "preprocessor.joblib"
XGB_PATH = MODELS_DIR / "individual" / "xgb_model.joblib"
YOLO_PATH = MODELS_DIR / "yolo" / "best.pt"
METADATA_PATH = MODELS_DIR / "preprocessing_metadata.json"

# ── Lazy globals ───────────────────────────────────────────────────────
_ensemble: Any | None = None
_preprocessor: Any | None = None
_xgb_model: Any | None = None
_yolo_wrapper: Any | None = None
_feature_names: list[str] = []


def _load_models() -> None:
    global _ensemble, _preprocessor, _xgb_model, _yolo_wrapper, _feature_names

    logger.info("Loading ensemble model…")
    _ensemble = joblib.load(ENSEMBLE_PATH)

    logger.info("Loading preprocessor…")
    _preprocessor = joblib.load(PREPROCESSOR_PATH)

    logger.info("Loading XGBoost model for SHAP…")
    _xgb_model = joblib.load(XGB_PATH)

    if METADATA_PATH.exists():
        meta = json.loads(METADATA_PATH.read_text())
        _feature_names = meta.get("feature_names", [])

    if YOLO_PATH.exists():
        logger.info("Loading YOLO model…")
        try:
            from ml_models.yolo_module.yolo_model import YOLOModelWrapper, YOLOConfig
            _yolo_wrapper = YOLOModelWrapper(weights_path=str(YOLO_PATH), config=YOLOConfig())
        except Exception as exc:
            logger.warning("YOLO model failed to load (damage endpoint unavailable): %s", exc)
    else:
        logger.warning("YOLO weights not found at %s — damage endpoint disabled.", YOLO_PATH)


# ── Input schema ───────────────────────────────────────────────────────
class ClaimInput(BaseModel):
    policy_type: str = Field("Comprehensive", description="Comprehensive | Third Party | Collision | Liability")
    claim_amount: float = Field(10000.0, ge=0)
    accident_date: str = Field("2024-01-15", description="YYYY-MM-DD")
    accident_location: str = Field("Urban", description="Free text — Rural/Urban detected automatically")
    vehicle_age: int = Field(5, ge=0, le=40)
    vehicle_make: str = Field("Honda")
    vehicle_model: str = Field("Civic")
    driver_age: int = Field(35, ge=16, le=100)
    driver_experience_years: int = Field(10, ge=0, le=80)
    previous_claims: int = Field(0, ge=0, le=20)
    witness: str = Field("No", description="Yes | No")
    police_report: str = Field("No", description="Yes | No")


# ── Feature engineering ────────────────────────────────────────────────
def _age_of_vehicle_bucket(years: int) -> str:
    if years == 0:
        return "new"
    if years <= 7:
        return f"{years} years"
    return "more than 7"


def _age_of_holder_bucket(age: int) -> str:
    if age <= 17:   return "16 to 17"
    if age <= 20:   return "18 to 20"
    if age <= 25:   return "21 to 25"
    if age <= 30:   return "26 to 30"
    if age <= 35:   return "31 to 35"
    if age <= 40:   return "36 to 40"
    if age <= 50:   return "41 to 50"
    if age <= 65:   return "51 to 65"
    return "over 65"


def _map_policy_type(pt: str) -> tuple[str, str, str]:
    """Returns (policy_type_col, base_policy, vehicle_category)."""
    pt = pt.strip().lower()
    if "third" in pt:
        return "Sedan - Liability", "Liability", "Sedan"
    if "collision" in pt:
        return "Sedan - Collision", "Collision", "Sedan"
    if "liability" in pt:
        return "Sedan - Liability", "Liability", "Sedan"
    return "Sedan - All Perils", "All Perils", "Sedan"


def build_input_df(claim: ClaimInput) -> pd.DataFrame:
    try:
        dt = datetime.strptime(claim.accident_date, "%Y-%m-%d")
        month = dt.strftime("%b")          # "Jan"
        day_of_week = dt.strftime("%A")    # "Monday"
        week_of_month = (dt.day - 1) // 7 + 1
        year = dt.year
    except ValueError:
        month, day_of_week, week_of_month, year = "Jan", "Monday", 1, 2024

    acc_loc = "Rural" if "rural" in claim.accident_location.lower() else "Urban"
    policy_type_col, base_policy, veh_cat = _map_policy_type(claim.policy_type)
    age_of_vehicle = _age_of_vehicle_bucket(claim.vehicle_age)
    age_of_holder = _age_of_holder_bucket(claim.driver_age)

    driver_rating = max(1, min(4, 4 - claim.driver_experience_years // 10))
    make = claim.vehicle_make.strip().capitalize()

    row: dict[str, Any] = {
        "Month": month,
        "DayOfWeek": day_of_week,
        "WeekOfMonth": week_of_month,
        "DayOfWeekClaimed": day_of_week,
        "MonthClaimed": month,
        "WeekOfMonthClaimed": week_of_month,
        "Make": make,
        "accident_location": acc_loc,
        "Sex": "Male",
        "MaritalStatus": "Single",
        "Fault": "Policy Holder",
        "policy_type": policy_type_col,
        "VehicleCategory": veh_cat,
        "VehiclePrice": "20,000 to 29,000",
        "Days:Policy-Accident": "more than 30",
        "Days:Policy-Claim": "more than 30",
        "AgeOfVehicle": age_of_vehicle,
        "AgeOfPolicyHolder": age_of_holder,
        "PoliceReportFiled": claim.police_report,
        "WitnessPresent": claim.witness,
        "AgentType": "Internal",
        "NumberOfSuppliments": "none",
        "AddressChange-Claim": "no change",
        "NumberOfCars": "1 vehicle",
        "BasePolicy": base_policy,
        # Numerical
        "driver_age": claim.driver_age,
        "previous_claims": claim.previous_claims,
        "PolicyNumber": 100000,
        "RepNumber": 5,
        "Deductible": 500,
        "DriverRating": driver_rating,
        "Year": year,
    }
    return pd.DataFrame([row])


# ── SHAP helper ────────────────────────────────────────────────────────
def compute_shap(x_processed: np.ndarray) -> dict[str, float]:
    if _xgb_model is None:
        return {}

    try:
        import shap
        xgb_estimator = getattr(_xgb_model, "model", _xgb_model)
        explainer = shap.TreeExplainer(xgb_estimator)
        shap_vals = explainer.shap_values(x_processed)
        if shap_vals.ndim == 2:
            values = shap_vals[0].tolist()
        else:
            values = shap_vals.tolist()

        # Map to feature names; fall back to indices
        names = _feature_names if len(_feature_names) == len(values) else [
            f"feature_{i}" for i in range(len(values))
        ]
        result = {name: round(float(v), 5) for name, v in zip(names, values)}
        # Return only top 15 by absolute value to keep payload small
        top = sorted(result.items(), key=lambda kv: abs(kv[1]), reverse=True)[:15]
        return dict(top)
    except Exception as exc:
        logger.warning("SHAP computation failed: %s", exc)
        return {}


# ── FastAPI app ────────────────────────────────────────────────────────
app = FastAPI(
    title="Insurance Fraud ML API",
    description="Fraud scoring (ensemble) + Vehicle damage detection (YOLOv11)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    _load_models()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "ensemble": _ensemble is not None,
        "yolo": _yolo_wrapper is not None,
    }


@app.post("/predict/fraud")
def predict_fraud(claim: ClaimInput) -> dict:
    if _ensemble is None or _preprocessor is None:
        raise HTTPException(status_code=503, detail="Models not loaded")

    try:
        input_df = build_input_df(claim)
        x_processed = _preprocessor.transform(input_df)
        proba = _ensemble.predict_proba(x_processed)
        fraud_score = float(proba[0, 1])
        shap_values = compute_shap(x_processed)

        return {
            "fraud_score": round(fraud_score, 4),
            "ensemble_score": round(fraud_score, 4),
            "fusion_score": round(min(1.0, fraud_score * 1.02), 4),
            "shap_values": shap_values,
        }
    except Exception as exc:
        logger.exception("Fraud prediction error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/predict/damage")
async def predict_damage(image: UploadFile = File(...)) -> dict:
    if _yolo_wrapper is None:
        raise HTTPException(status_code=503, detail="YOLO model not loaded")

    try:
        from ml_models.yolo_module.inference import process_single_image
        from PIL import Image as PILImage
        import tempfile, os

        contents = await image.read()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            result = process_single_image(
                model_wrapper=_yolo_wrapper,
                image_path=tmp_path,
                conf_threshold=0.25,
            )
        finally:
            os.unlink(tmp_path)

        detections = result.get("detections", [])
        bounding_boxes = [
            {
                "x": int(d["bbox"][0]),
                "y": int(d["bbox"][1]),
                "w": int(d["bbox"][2] - d["bbox"][0]),
                "h": int(d["bbox"][3] - d["bbox"][1]),
                "class": d.get("class_name", "damage"),
                "confidence": round(d["confidence"], 3),
            }
            for d in detections
        ]
        severity = min(1.0, len(detections) * 0.25) if detections else 0.1
        affected_parts = list({d.get("class_name", "body") for d in detections}) or ["body"]

        return {
            "bounding_boxes": bounding_boxes,
            "severity_score": round(severity, 3),
            "affected_parts": affected_parts,
            "detection_count": len(detections),
        }
    except Exception as exc:
        logger.exception("Damage detection error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)
