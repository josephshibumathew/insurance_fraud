"""Fraud detection API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, get_ml_models
from app.schemas.fraud import FraudBatchRequest, FraudBatchResponse, FraudPredictRequest, FraudResultResponse
from app.services.fraud_service import FraudService

router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.post("/predict", response_model=FraudResultResponse)
def predict(payload: FraudPredictRequest, db: Session = Depends(get_db), _models=Depends(get_ml_models), _current_user=Depends(get_current_user)):
	service = FraudService(db)
	try:
		prediction = service.predict_for_claim(payload.claim_id)
	except ValueError as exc:
		raise HTTPException(status_code=404, detail=str(exc)) from exc
	return FraudResultResponse.model_validate(prediction)


@router.get("/status/{claim_id}")
def prediction_status(claim_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
	prediction = FraudService(db).get_latest_prediction(claim_id)
	return {"claim_id": claim_id, "status": "completed" if prediction else "pending"}


@router.get("/results/{claim_id}", response_model=FraudResultResponse)
def prediction_results(claim_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
	prediction = FraudService(db).get_latest_prediction(claim_id)
	if prediction is None:
		raise HTTPException(status_code=404, detail="No prediction found")
	return FraudResultResponse.model_validate(prediction)


@router.post("/batch", response_model=FraudBatchResponse)
def batch_predict(payload: FraudBatchRequest, db: Session = Depends(get_db), _models=Depends(get_ml_models), _current_user=Depends(get_current_user)):
	service = FraudService(db)
	try:
		outputs = service.batch_predict(payload.claim_ids)
	except ValueError as exc:
		raise HTTPException(status_code=404, detail=str(exc)) from exc
	return FraudBatchResponse(results=[FraudResultResponse.model_validate(item) for item in outputs])

