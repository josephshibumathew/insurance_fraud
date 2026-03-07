"""Image compression helpers before model processing."""

from __future__ import annotations

import io


def compress_image_bytes(image_bytes: bytes, quality: int = 82, max_dimension: int = 1280) -> bytes:
    """Compress image bytes using Pillow when available; fallback returns original."""
    try:
        from PIL import Image
    except Exception:
        return image_bytes

    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        img.thumbnail((max_dimension, max_dimension))
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        return output.getvalue()
