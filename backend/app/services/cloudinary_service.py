"""
Cloudinary upload service.

Reuses the connectivity logic proven in `scripts/test_cloudinary.py`
(config from env vars, upload via `cloudinary.uploader.upload`).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")


class CloudinaryConfigError(RuntimeError):
    """Raised when Cloudinary credentials are missing or incomplete."""


def configure_cloudinary() -> None:
    """Read Cloudinary credentials from the environment and configure the SDK."""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        raise CloudinaryConfigError(
            "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET in .env"
        )

    import cloudinary

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )


def upload_image(file_path: str | Path, public_id: str | None = None) -> dict:
    """
    Upload an image file to Cloudinary.

    Mirrors the upload call from `scripts/test_cloudinary.py`:
    `cloudinary.uploader.upload(file_path, public_id=...)`.

    Returns a dict with `url` (secure URL) and `public_id`.
    """
    configure_cloudinary()

    import cloudinary.uploader

    result = cloudinary.uploader.upload(str(file_path), public_id=public_id)

    return {
        "url": result.get("secure_url"),
        "public_id": result.get("public_id"),
    }
