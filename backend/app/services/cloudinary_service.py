import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")


class CloudinaryConfigError(RuntimeError):
    pass


def configure_cloudinary() -> None:
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
    try:
        configure_cloudinary()
        import cloudinary.uploader
        result = cloudinary.uploader.upload(str(file_path), public_id=public_id)
        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
        }
    except CloudinaryConfigError as e:
        import logging
        import shutil
        import uuid

        logger = logging.getLogger(__name__)
        logger.warning("Cloudinary unconfigured (%s); storing image locally.", e)
        uploads_dir = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}_{Path(file_path).name}"
        dest_path = uploads_dir / filename
        shutil.copyfile(str(file_path), str(dest_path))
        return {
            "url": str(dest_path),
            "public_id": public_id or filename,
        }
