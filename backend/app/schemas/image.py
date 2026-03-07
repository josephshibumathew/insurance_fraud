"""Image processing schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: int
    claim_id: int
    filename: str
    processed: bool
    damage_results: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class DamageResultResponse(BaseModel):
    image_id: int
    damage_results: dict
