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

            try:
                _processor = CLIPProcessor.from_pretrained(model_name, local_files_only=True)
                _model = CLIPModel.from_pretrained(model_name, local_files_only=True)
            except Exception:
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
            if not isinstance(image_features, torch.Tensor):
                if hasattr(image_features, "pooler_output") and image_features.pooler_output is not None:
                    image_features = image_features.pooler_output
                elif hasattr(image_features, "image_embeds") and image_features.image_embeds is not None:
                    image_features = image_features.image_embeds
                elif hasattr(image_features, "last_hidden_state") and image_features.last_hidden_state is not None:
                    image_features = image_features.last_hidden_state[:, 0, :]
                else:
                    image_features = image_features[0]

            image_features = image_features / image_features.norm(
                p=2, dim=-1, keepdim=True
            )
            vector = image_features[0].tolist()

        return [float(x) for x in vector]
    except Exception as e:
        raise EmbeddingServiceError(
            f"CLIP embedding inference failed: {e}"
        ) from e


def generate_text_embedding(text: str) -> list[float]:
    """
    Generate a normalized CLIP text embedding sharing the exact same
    vector space as the wardrobe image embeddings in ChromaDB.
    """
    if not text or not str(text).strip():
        raise EmbeddingServiceError("No text provided for embedding.")

    try:
        import torch

        model, processor = _get_model_and_processor()
        inputs = processor(text=[str(text).strip()], return_tensors="pt", padding=True, truncation=True)

        with torch.no_grad():
            text_features = model.get_text_features(**inputs)
            if not isinstance(text_features, torch.Tensor):
                if hasattr(text_features, "pooler_output") and text_features.pooler_output is not None:
                    text_features = text_features.pooler_output
                elif hasattr(text_features, "text_embeds") and text_features.text_embeds is not None:
                    text_features = text_features.text_embeds
                elif hasattr(text_features, "last_hidden_state") and text_features.last_hidden_state is not None:
                    text_features = text_features.last_hidden_state[:, 0, :]
                else:
                    text_features = text_features[0]

            text_features = text_features / text_features.norm(
                p=2, dim=-1, keepdim=True
            )
            vector = text_features[0].tolist()

        return [float(x) for x in vector]
    except Exception as e:
        raise EmbeddingServiceError(
            f"CLIP text embedding inference failed: {e}"
        ) from e

