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
    pass


DEFAULT_CLIP_MODEL = "openai/clip-vit-base-patch32"

_processor = None
_model = None


def _get_model_and_processor():
    global _processor, _model
    if _processor is None or _model is None:
        model_name = os.getenv("CLIP_MODEL_NAME", DEFAULT_CLIP_MODEL)
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
    if not image_url_or_path:
        raise EmbeddingServiceError("No image URL or file path provided.")

    try:
        if image_url_or_path.startswith("http://") or image_url_or_path.startswith("https://"):
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
            image_features = image_features / image_features.norm(
                p=2, dim=-1, keepdim=True
            )
            vector = image_features[0].tolist()

        return [float(x) for x in vector]
    except Exception as e:
        raise EmbeddingServiceError(
            f"CLIP embedding inference failed: {e}"
        ) from e
