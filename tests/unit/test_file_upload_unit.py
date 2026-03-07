from __future__ import annotations

import asyncio

from fastapi import UploadFile

from app.services.image_service import ImageService


def test_file_upload_handling(test_db, test_user, sample_images, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))

    service = ImageService(test_db)
    sample = sample_images[0]
    upload = UploadFile(filename=sample[0], file=sample[1])

    image = asyncio.run(service.store_image(claim_id=1, image_file=upload))
    assert image.filename
    assert image.processed is True
    assert "severity_score" in image.damage_results
