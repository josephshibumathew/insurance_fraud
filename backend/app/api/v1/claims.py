"""Claims API routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.claim import ClaimCreateRequest, ClaimListResponse, ClaimResponse, ClaimUpdateRequest
from app.schemas.image import ImageResponse
from app.schemas.response import APIMessage
from app.services.claim_service import ClaimService
from app.services.image_service import ImageService

router = APIRouter(prefix="/claims", tags=["claims"])


def _ensure_claim_access(claim, current_user: User) -> None:
	if claim is None:
		raise HTTPException(status_code=404, detail="Claim not found")
	if current_user.role != "admin" and claim.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Not authorized for this claim")


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
	policy_number: str | None = Form(default=None),
	claim_amount: float | None = Form(default=None),
	accident_date: str | None = Form(default=None),
	csv_file: UploadFile | None = File(default=None),
	db: Session = Depends(get_db),
	current_user: User = Depends(require_role("surveyor")),
):
	service = ClaimService(db)
	if csv_file is not None:
		created = await service.create_claims_from_csv(current_user.id, csv_file)
		if not created:
			raise HTTPException(status_code=400, detail="No valid claims found in CSV")
		return ClaimResponse.model_validate(created[0])

	if policy_number is None or claim_amount is None or accident_date is None:
		raise HTTPException(status_code=422, detail="Provide policy_number, claim_amount, accident_date or CSV file")

	payload = ClaimCreateRequest(policy_number=policy_number, claim_amount=claim_amount, accident_date=date.fromisoformat(accident_date))
	claim = service.create_claim(current_user.id, payload.policy_number, payload.claim_amount, payload.accident_date)
	return ClaimResponse.model_validate(claim)


@router.get("", response_model=ClaimListResponse)
def list_claims(
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=20, ge=1, le=100),
	status: str | None = Query(default=None),
	policy_number: str | None = Query(default=None),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	service = ClaimService(db)
	owner_id = None if current_user.role == "admin" else current_user.id
	items, total = service.list_claims(page=page, page_size=page_size, status=status, policy_number=policy_number, user_id=owner_id)
	return ClaimListResponse(items=[ClaimResponse.model_validate(i) for i in items], total=total, page=page, page_size=page_size)


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	service = ClaimService(db)
	claim = service.get_claim(claim_id)
	_ensure_claim_access(claim, current_user)
	return ClaimResponse.model_validate(claim)


@router.put("/{claim_id}", response_model=ClaimResponse)
def update_claim(claim_id: int, payload: ClaimUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	service = ClaimService(db)
	claim = service.get_claim(claim_id)
	_ensure_claim_access(claim, current_user)
	updated = service.update_claim(claim, payload.model_dump())
	return ClaimResponse.model_validate(updated)


@router.delete("/{claim_id}", response_model=APIMessage)
def delete_claim(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	service = ClaimService(db)
	claim = service.get_claim(claim_id)
	_ensure_claim_access(claim, current_user)
	service.delete_claim(claim)
	return APIMessage(message="Claim deleted")


@router.post("/{claim_id}/images", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_claim_image(
	claim_id: int,
	image_file: UploadFile = File(...),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	claim_service = ClaimService(db)
	claim = claim_service.get_claim(claim_id)
	_ensure_claim_access(claim, current_user)
	image = await ImageService(db).store_image(claim_id, image_file)
	return ImageResponse.model_validate(image)


@router.get("/{claim_id}/images", response_model=list[ImageResponse])
def list_claim_images(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	claim_service = ClaimService(db)
	claim = claim_service.get_claim(claim_id)
	_ensure_claim_access(claim, current_user)
	images = ImageService(db).list_claim_images(claim_id)
	return [ImageResponse.model_validate(i) for i in images]

