"""
Vision Agent: LLM-based garment attribute extraction (MILESTONES 7 + 8).

Takes an image URL and returns {category, color, pattern, style, season,
material} using Google Gemini's structured-output mode (response_schema
JSON schema) — no free-text parsing.

Model is read from `GEMINI_VISION_MODEL` (defaults to gemini-3.5-flash)
so it can be swapped without a code change.
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")


class VisionServiceError(RuntimeError):
    """Raised when attribute extraction fails (config, API, or parsing)."""


DEFAULT_MODEL = "gemini-3.5-flash"
REQUEST_TIMEOUT_MS = 60_000  # HttpOptions.timeout is in milliseconds
MAX_RATE_LIMIT_RETRIES = 3  # 429/503 -> retry with backoff before giving up

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
    """Infer the image MIME type from the URL so Gemini receives the right kind."""
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
    """Fetch image bytes from URL and wrap in Part.from_bytes for Gemini vision."""
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


def analyze_image(image_url: str) -> dict:
    """Extract 6 garment attributes from an image URL via Gemini vision.

    Returns {category, color, pattern, style, season, material}.
    Raises VisionServiceError with a clear message on any failure; never
    propagates raw SDK exceptions.
    """
    if not image_url:
        raise VisionServiceError("No image URL provided.")

    model = os.getenv("GEMINI_VISION_MODEL", DEFAULT_MODEL)
    client = _get_client()

    from google.genai import types

    image_part = _fetch_image_part(image_url)

    response = None
    last_error: Exception | None = None
    for attempt in range(MAX_RATE_LIMIT_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    image_part,
                    types.Part.from_text(
                        text="Describe the garment in this photo. Respond with JSON."
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=OUTPUT_SCHEMA,
                ),
            )
            break
        except Exception as e:
            last_error = e
            if _is_rate_limit(e) and attempt < MAX_RATE_LIMIT_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))  # 2s, 4s backoff
                continue
            raise VisionServiceError(f"Gemini vision request failed: {e}") from e

    if response is None:
        raise VisionServiceError(
            f"Gemini vision request failed: {last_error}"
        ) from last_error

    try:
        if getattr(response, "parsed", None) is not None:
            data = dict(response.parsed)
        else:
            content = response.text
            if not content:
                raise ValueError("empty response body")
            data = json.loads(content)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise VisionServiceError(f"Could not parse Gemini response: {e}") from e

    required = {"category", "color", "pattern", "style", "season", "material"}
    missing = required - set(data)
    if missing:
        raise VisionServiceError(f"Gemini response missing fields: {sorted(missing)}")

    return {
        "category": data["category"],
        "color": data["color"],
        "pattern": data["pattern"],
        "style": data["style"],
        "season": data["season"],
        "material": data["material"],
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
    """Analyze a virtual try-on render image to derive fit tightness, silhouette, and notes.

    Returns {fit_tightness, silhouette, notes}.
    Raises VisionServiceError with a clear message on any failure.
    """
    if not render_image_url:
        raise VisionServiceError("No render image URL provided.")

    model = os.getenv("GEMINI_VISION_MODEL", DEFAULT_MODEL)
    client = _get_client()

    from google.genai import types

    image_part = _fetch_image_part(render_image_url)

    response = None
    last_error: Exception | None = None
    for attempt in range(MAX_RATE_LIMIT_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    image_part,
                    types.Part.from_text(
                        text="Analyze the fit and silhouette of the garment in this try-on render photo. Respond with JSON."
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=FIT_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=FIT_OUTPUT_SCHEMA,
                ),
            )
            break
        except Exception as e:
            last_error = e
            if _is_rate_limit(e) and attempt < MAX_RATE_LIMIT_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            raise VisionServiceError(f"Gemini fit vision request failed: {e}") from e

    if response is None:
        raise VisionServiceError(
            f"Gemini fit vision request failed: {last_error}"
        ) from last_error

    try:
        if getattr(response, "parsed", None) is not None:
            data = dict(response.parsed)
        else:
            content = response.text
            if not content:
                raise ValueError("empty response body")
            data = json.loads(content)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise VisionServiceError(f"Could not parse Gemini fit response: {e}") from e

    required = {"fit_tightness", "silhouette", "notes"}
    missing = required - set(data)
    if missing:
        raise VisionServiceError(f"Gemini fit response missing fields: {sorted(missing)}")

    allowed_tightness = {"tight", "regular", "loose", "oversized"}
    allowed_silhouette = {"slim", "tailored", "relaxed", "boxy"}

    fit_tightness = str(data.get("fit_tightness", "")).lower()
    if fit_tightness not in allowed_tightness:
        fit_tightness = "regular"

    silhouette = str(data.get("silhouette", "")).lower()
    if silhouette not in allowed_silhouette:
        silhouette = "tailored"

    notes = str(data.get("notes", ""))

    return {
        "fit_tightness": fit_tightness,
        "silhouette": silhouette,
        "notes": notes,
    }

