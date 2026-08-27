"""
Embedding Service (MILESTONE 12).

Generates 512-dimensional normalized image embedding vectors locally via
Hugging Face `transformers` CLIP model (`openai/clip-vit-base-patch32`).
Runs on CPU without external API key or billing dependencies.
"""

import io
import logging
import os
from pathlib import Path

import requests
import urllib3
from PIL import Image

urllib3.disable_warnings()

logger = logging.getLogger(__name__)


class EmbeddingServiceError(RuntimeError):
    """Raised when image embedding generation fails."""


DEFAULT_CLIP_MODEL = "openai/clip-vit-base-patch32"

_processor = None
_model = None


def _get_model_and_processor():
    """Lazily load and cache the CLIP model and processor on CPU."""
    global _processor, _model
    if _processor is None or _model is None:
        model_name = os.getenv("CLIP_MODEL_NAME", DEFAULT_CLIP_MODEL)
        logger.info("Loading local CLIP model on CPU: %s", model_name)
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            _processor = CLIPProcessor.from_pretrained(model_name)
            _model = CLIPModel.from_pretrained(model_name)
            _model.eval()
        except Exception as e:
            raise EmbeddingServiceError(
                f"Failed to load CLIP model '{model_name}': {e}"
            ) from e
    return _model, _processor


def generate_embedding(image_url_or_path: str) -> list[float]:
    """Generate a normalized 512-dimensional CLIP embedding vector for an image.

    Accepts an HTTP/HTTPS image URL or a local file path.
    Returns a Python list of 512 float values.
    Raises EmbeddingServiceError on any image load or model inference failure.
    """
    if not image_url_or_path:
        raise EmbeddingServiceError("No image URL or file path provided.")

    try:
        if image_url_or_path.startswith("http://") or image_url_or_path.startswith(
            "https://"
        ):
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(image_url_or_path, headers=headers, timeout=15, verify=False)
            resp.raise_for_status()
            image = Image.open(io.BytesIO(resp.content)).convert("RGB")
        else:
            local_path = Path(image_url_or_path)
            if not local_path.exists():
                raise FileNotFoundError(f"Local file not found: {image_url_or_path}")
            image = Image.open(local_path).convert("RGB")
    except Exception as e:
        raise EmbeddingServiceError(
            f"Failed to load image from '{image_url_or_path}': {e}"
        ) from e

    try:
        import torch

        model, processor = _get_model_and_processor()
        inputs = processor(images=image, return_tensors="pt")

        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
            # L2 normalize vector
            image_features = image_features / image_features.norm(
                p=2, dim=-1, keepdim=True
            )
            vector = image_features[0].tolist()

        return [float(x) for x in vector]
    except Exception as e:
        raise EmbeddingServiceError(
            f"CLIP embedding inference failed: {e}"
        ) from e
