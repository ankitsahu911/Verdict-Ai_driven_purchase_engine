import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")


class VisionServiceError(RuntimeError):
    pass


DEFAULT_MODEL = "gemini-3.5-flash"
REQUEST_TIMEOUT_MS = 60_000
MAX_RATE_LIMIT_RETRIES = 3

SYSTEM_PROMPT = """You are an expert garment attribute extractor for a fashion AI.
Analyze the garment photo and return exactly six attributes:

- "category": the garment type. Suggested vocabulary: top, bottom, dress,
  outerwear, footwear, accessory. Use your best judgment for anything else;
  only return "unknown" when no garment is clearly visible.
- "color": the dominant color(s) of the garment, one or two words
  (e.g. "navy", "black", "floral red").
- "pattern": the fabric pattern, e.g. "solid", "striped", "plaid",
  "floral", "polka dot". Use "solid" when there is no pattern.
- "style": the style category. Suggested vocabulary: casual, formal,
  smart-casual, athletic, streetwear, bohemian, minimalist. Pick the
  closest match.
- "season": the season this garment is best suited for. Suggested
  vocabulary: summer, winter, monsoon, all-season. Use your best
  judgment; prefer "all-season" when uncertain.
- "material": the likely fabric/material. Suggested vocabulary: cotton,
  denim, wool, silk, leather, synthetic, linen, cashmere, polyester.
  This is a best-guess from the photo — note it is an estimate.

Be concise and factual. Base everything on what you actually see."""

OUTPUT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "category": {"type": "STRING"},
        "color": {"type": "STRING"},
        "pattern": {"type": "STRING"},
        "style": {"type": "STRING"},
        "season": {"type": "STRING"},
        "material": {"type": "STRING"},
    },
    "required": ["category", "color", "pattern", "style", "season", "material"],
}


def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise VisionServiceError(
            "GEMINI_API_KEY is not set. Get a free key at "
            "https://aistudio.google.com/app/apikey and add it to .env"
        )

    from google import genai

    return genai.Client(
        api_key=api_key,
        http_options={"timeout": REQUEST_TIMEOUT_MS},
    )


def _guess_mime(image_url: str) -> str:
    ext = Path(image_url.split("?")[0]).suffix.lower()
    return {
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".avif": "image/avif",
        ".jpeg": "image/jpeg",
        ".jpg": "image/jpeg",
    }.get(ext, "image/jpeg")


def _is_rate_limit(e: Exception) -> bool:
    err_str = str(e)
    return (
        getattr(e, "code", None) == 429
        or "429" in err_str
        or "RESOURCE_EXHAUSTED" in err_str
    )


def _fetch_image_part(image_url: str):
    from google.genai import types
    mime = _guess_mime(image_url)
    try:
        import urllib3
        urllib3.disable_warnings()
        import requests
        resp = requests.get(image_url, timeout=15, verify=False)
        if resp.status_code == 200 and resp.content:
            content_type = resp.headers.get("content-type", "").split(";")[0].strip()
            if content_type and content_type.startswith("image/"):
                mime = content_type
            return types.Part.from_bytes(data=resp.content, mime_type=mime)
    except Exception:
        pass
    return types.Part.from_uri(file_uri=image_url, mime_type=mime)


from app.services.llm_provider import get_vision_completion


def analyze_image(image_url: str) -> dict:
    if not image_url:
        raise VisionServiceError("No image URL provided.")

    if os.path.exists(image_url):
        try:
            from PIL import Image

            with Image.open(image_url) as img:
                img.verify()
        except Exception as img_err:
            raise VisionServiceError(
                f"couldn't read this image — file is corrupted or unreadable: {img_err}"
            )

    try:
        completion = get_vision_completion(
            prompt="Describe the garment in this photo. Respond with JSON.",
            image_url=image_url,
            system_instruction=SYSTEM_PROMPT,
            response_schema=OUTPUT_SCHEMA,
        )
    except Exception as e:
        if "couldn't read this image" in str(e).lower():
            raise VisionServiceError(str(e)) from e
        raise VisionServiceError(f"Gemini vision request failed: {e}") from e

    data = completion.data
    if not isinstance(data, dict):
        raise VisionServiceError(f"Could not parse vision response: invalid data type {type(data)}")

    # For local/fallback models, provide sensible fallbacks for any missing attributes
    category = str(data.get("category", "unknown") or "unknown").lower().strip()
    color = str(data.get("color", "unknown") or "unknown").strip()
    pattern = str(data.get("pattern", "solid") or "solid").strip()
    style = str(data.get("style", "casual") or "casual").strip()
    season = str(data.get("season", "all-season") or "all-season").strip()
    material = str(data.get("material", "cotton") or "cotton").strip()

    return {
        "category": category,
        "color": color,
        "pattern": pattern,
        "style": style,
        "season": season,
        "material": material,
        "provider_used": completion.provider_used,
    }


FIT_SYSTEM_PROMPT = """You are an expert fit and silhouette analyzer for a virtual try-on fashion AI.
Analyze the rendered try-on image (showing a model/person wearing a garment) and derive three structured fit attributes:

- "fit_tightness": how tightly or loosely the garment fits on the model's body.
  Must be strictly one of: "tight", "regular", "loose", "oversized".
- "silhouette": the overall structural shape/cut of the garment on the model.
  Must be strictly one of: "slim", "tailored", "relaxed", "boxy".
- "notes": a concise, plain-English observation (1-2 sentences max) describing the fit and silhouette on the body (e.g., "Slightly snug around waist with natural shoulder drape.").

Be objective, concise, and base your analysis directly on the visual fit shown in the try-on render."""

FIT_OUTPUT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "fit_tightness": {
            "type": "STRING",
            "enum": ["tight", "regular", "loose", "oversized"],
        },
        "silhouette": {
            "type": "STRING",
            "enum": ["slim", "tailored", "relaxed", "boxy"],
        },
        "notes": {"type": "STRING"},
    },
    "required": ["fit_tightness", "silhouette", "notes"],
}


def analyze_fit(render_image_url: str) -> dict:
    if not render_image_url:
        raise VisionServiceError("No render image URL provided.")

    try:
        completion = get_vision_completion(
            prompt="Analyze the fit and silhouette of the garment in this try-on render photo. Respond with JSON.",
            image_url=render_image_url,
            system_instruction=FIT_SYSTEM_PROMPT,
            response_schema=FIT_OUTPUT_SCHEMA,
        )
    except Exception as e:
        raise VisionServiceError(f"Fit vision request failed: {e}") from e

    data = completion.data
    if not isinstance(data, dict):
        raise VisionServiceError(f"Could not parse fit vision response: {data}")

    allowed_tightness = {"tight", "regular", "loose", "oversized"}
    allowed_silhouette = {"slim", "tailored", "relaxed", "boxy"}

    fit_tightness = str(data.get("fit_tightness", "")).lower().strip()
    if fit_tightness not in allowed_tightness:
        fit_tightness = "regular"

    silhouette = str(data.get("silhouette", "")).lower().strip()
    if silhouette not in allowed_silhouette:
        silhouette = "tailored"

    notes = str(data.get("notes", "")).strip()
    if not notes:
        notes = "Visual fit assessment completed."

    return {
        "fit_tightness": fit_tightness,
        "silhouette": silhouette,
        "notes": notes,
        "provider_used": completion.provider_used,
    }

