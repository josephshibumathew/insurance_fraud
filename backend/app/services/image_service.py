"""Image management and processing service."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path
from random import Random
from typing import Any

def _get_sqlalchemy_select():
    try:
        sqlalchemy_module = importlib.import_module("sqlalchemy")
        return getattr(sqlalchemy_module, "select")
    except Exception as exc:
        raise ImportError("sqlalchemy is required for image service") from exc


Session = Any
UploadFile = Any

from app.core.config import get_settings
from app.models.image import Image

_rng = Random(7)


def _call_damage_api(file_bytes: bytes, filename: str, settings) -> dict | None:
    """Call HF Space damage API if ML_API_URL is configured."""
    if not settings.ml_api_url:
        return None
    try:
        import httpx
        url = settings.ml_api_url.rstrip("/") + "/predict/damage"
        response = httpx.post(
            url,
            files={"image": (filename, file_bytes, "image/jpeg")},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        import logging
        logging.getLogger("fraud-api").warning("Damage API call failed, using fallback: %s", exc)
        return None


class ImageService:
    def __init__(self, db: Any) -> None:
        self.db = db
        self.settings = get_settings()

    async def store_image(self, claim_id: int, image_file: UploadFile) -> Image:
        uploads_dir = Path(self.settings.uploads_dir)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        filename = f"claim_{claim_id}_{int(datetime.now(UTC).timestamp())}_{image_file.filename}"
        file_path = uploads_dir / filename
        content = await image_file.read()
        file_path.write_bytes(content)

        ml_result = _call_damage_api(content, image_file.filename or "image.jpg", self.settings)

        if ml_result:
            damage_results = {
                "severity_score": ml_result.get("severity_score", 0.5),
                "count_by_damage_type": {"damage": ml_result.get("detection_count", 1)},
                "affected_parts": ml_result.get("affected_parts", ["body"]),
                "bounding_boxes": ml_result.get("bounding_boxes", []),
            }
        else:
            damage_results = {
                "severity_score": round(_rng.uniform(0.1, 0.95), 3),
                "count_by_damage_type": {"scratch": _rng.randint(0, 3), "dent": _rng.randint(0, 2)},
                "affected_parts": ["bumper", "door"],
                "bounding_boxes": [{"x": 30, "y": 45, "w": 80, "h": 60}],
            }

        image = Image(
            claim_id=claim_id,
            filename=str(file_path),
            processed=True,
            damage_results=damage_results,
            created_at=datetime.now(UTC),
        )
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        return image

    def list_claim_images(self, claim_id: int) -> list[Image]:
        select = _get_sqlalchemy_select()
        stmt = select(Image).where(Image.claim_id == claim_id).order_by(Image.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_image(self, image_id: int) -> Image | None:
        return self.db.get(Image, image_id)
