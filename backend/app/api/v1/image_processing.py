"""Image processing API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.core.config import get_settings
from app.schemas.image import DamageResultResponse, ImageResponse
from app.services.image_service import ImageService

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/upload", response_model=ImageResponse)
async def upload_single_image(
	claim_id: int,
	image_file: UploadFile = File(...),
	db: Session = Depends(get_db),
	_current_user=Depends(get_current_user),
):
	image = await ImageService(db).store_image(claim_id, image_file)
	return ImageResponse.model_validate(image)


@router.post("/batch-upload", response_model=list[ImageResponse])
async def upload_batch_images(
	claim_id: int,
	image_files: list[UploadFile] = File(...),
	db: Session = Depends(get_db),
	_current_user=Depends(get_current_user),
):
	service = ImageService(db)
	results = []
	for file in image_files:
		results.append(await service.store_image(claim_id, file))
	return [ImageResponse.model_validate(item) for item in results]


@router.get("/{image_id}/damage", response_model=DamageResultResponse)
def get_damage_results(image_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
	image = ImageService(db).get_image(image_id)
	if image is None:
		raise HTTPException(status_code=404, detail="Image not found")
	return DamageResultResponse(image_id=image.id, damage_results=image.damage_results)


@router.get("/{image_id}/visualization")
def get_image_visualization(image_id: int, db: Session = Depends(get_db)):
	image = ImageService(db).get_image(image_id)
	if image is None:
		raise HTTPException(status_code=404, detail="Image not found")
	path = Path(image.filename)
	if not path.exists():
		fallback = Path(get_settings().uploads_dir) / path.name
		if fallback.exists():
			path = fallback
	if not path.exists():
		raise HTTPException(status_code=404, detail="Image file not found")
	return FileResponse(str(path), media_type="image/jpeg", filename=path.name)

