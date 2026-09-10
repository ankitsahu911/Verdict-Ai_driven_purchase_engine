"""
LLM Provider Abstraction Layer with Automatic Fallback.
Provides unified vision completion across cloud primary provider (Gemini)
and local Ollama fallback (e.g. llava).
"""

import base64
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
import requests

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

OLLAMA_DEFAULT_HOST = "http://localhost:11434"
OLLAMA_DEFAULT_VISION_MODEL = "llava"
DEFAULT_PRIMARY_MODEL = "gemini-3.5-flash"


class VisionCompletionResult:
    """Standardized result returned by vision provider abstraction."""

    def __init__(
        self,
        data: dict,
        provider_used: str,
        model_used: str,
        raw_text: str = "",
        error_reason: Optional[str] = None,
    ):
        self.data = data
        self.provider_used = provider_used  # "gemini" or "ollama_fallback"
        self.model_used = model_used
        self.raw_text = raw_text
        self.error_reason = error_reason

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "raw_text": self.raw_text,
            "error_reason": self.error_reason,
        }


def extract_json_from_text(text: str) -> dict:
    """Robustly parse JSON from raw completion text, handling markdown blocks and prose."""
    if not text:
        raise ValueError("Empty response text from LLM.")

    text = text.strip()

    # 1. Direct JSON parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Markdown fenced code block (```json ... ``` or ``` ... ```)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # 3. Substring between first '{' and last '}'
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON from text: {text[:200]}")


def fetch_image_base64(image_url: str) -> str:
    """Fetch image bytes from URL, file path, or data URI, and return base64 string."""
    if not image_url:
        raise ValueError("Image URL or path is empty.")

    raw_bytes: bytes
    # 1. Data URI
    if image_url.startswith("data:image/"):
        parts = image_url.split(",", 1)
        raw_bytes = base64.b64decode(parts[1] if len(parts) > 1 else parts[0])
    elif os.path.exists(image_url):
        # 2. Local file
        with open(image_url, "rb") as f:
            raw_bytes = f.read()
    else:
        # 3. HTTP / HTTPS URL
        import urllib3

        urllib3.disable_warnings()
        resp = requests.get(image_url, timeout=15, verify=False)
        resp.raise_for_status()
        raw_bytes = resp.content

    return base64.b64encode(raw_bytes).decode("utf-8")


def _fetch_gemini_image_part(image_url: str):
    """Create a Google GenAI Part for Gemini input."""
    from google.genai import types

    ext = Path(image_url.split("?")[0]).suffix.lower()
    mime = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".avif": "image/avif",
        ".jpeg": "image/jpeg",
        ".jpg": "image/jpeg",
    }.get(ext, "image/jpeg")

    raw_bytes: bytes
    if image_url.startswith("data:image/"):
        parts = image_url.split(",", 1)
        b64_data = parts[1] if len(parts) > 1 else parts[0]
        header = parts[0] if len(parts) > 1 else ""
        if "image/png" in header:
            mime = "image/png"
        elif "image/webp" in header:
            mime = "image/webp"
        raw_bytes = base64.b64decode(b64_data)
    elif os.path.exists(image_url):
        with open(image_url, "rb") as f:
            raw_bytes = f.read()
    else:
        import urllib3

        urllib3.disable_warnings()
        resp = requests.get(image_url, timeout=15, verify=False)
        raw_bytes = resp.content

    return types.Part.from_bytes(data=raw_bytes, mime_type=mime)


def _get_default_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set or empty. Primary cloud vision unavailable."
        )

    from google import genai

    return genai.Client(
        api_key=api_key,
        http_options={"timeout": 60_000},
    )


def call_gemini_vision(
    prompt: str,
    image_url: str,
    system_instruction: Optional[str] = None,
    response_schema: Optional[dict] = None,
    model: Optional[str] = None,
    client: Optional[Any] = None,
) -> dict:
    """Invoke primary Gemini vision model."""
    if client is None:
        try:
            import app.services.vision_service as vs_mod
            client_getter = getattr(vs_mod, "_get_client", _get_default_client)
            client = client_getter()
        except Exception:
            client = _get_default_client()

    model_name = model or os.getenv("GEMINI_VISION_MODEL", DEFAULT_PRIMARY_MODEL)

    from google.genai import types

    image_part = _fetch_gemini_image_part(image_url)

    config_kwargs: dict[str, Any] = {}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    if response_schema:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = response_schema
    else:
        config_kwargs["response_mime_type"] = "application/json"

    models_to_try = [model_name]
    for alt in ["gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]:
        if alt not in models_to_try:
            models_to_try.append(alt)

    response = None
    last_err = None
    for cur_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=cur_model,
                contents=[
                    image_part,
                    types.Part.from_text(text=prompt),
                ],
                config=types.GenerateContentConfig(**config_kwargs),
            )
            model_name = cur_model
            break
        except Exception as err:
            last_err = err
            err_str = str(err)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                logger.warning(
                    "[Gemini Vision] Model %s hit 429 rate limit; trying alternate free tier model...",
                    cur_model,
                )
                time.sleep(1.0)
                continue
            raise err

    if response is None:
        raise last_err

    if getattr(response, "parsed", None) is not None:
        data = dict(response.parsed)
    else:
        content = getattr(response, "text", "") or ""
        data = extract_json_from_text(content)

    return {
        "data": data,
        "raw_text": getattr(response, "text", ""),
        "model_used": model_name,
        "provider_used": "gemini",
    }


def call_ollama_vision(
    prompt: str,
    image_url: str,
    system_instruction: Optional[str] = None,
    timeout_sec: float = 60.0,
    model: Optional[str] = None,
    host: Optional[str] = None,
) -> dict:
    """Invoke local Ollama vision endpoint via HTTP POST."""
    host = (host or os.getenv("OLLAMA_HOST", OLLAMA_DEFAULT_HOST)).rstrip("/")
    model_name = model or os.getenv("OLLAMA_VISION_MODEL", OLLAMA_DEFAULT_VISION_MODEL)
    timeout = float(os.getenv("OLLAMA_TIMEOUT_SEC", str(timeout_sec)))

    image_b64 = fetch_image_base64(image_url)

    combined_prompt = prompt
    if system_instruction:
        combined_prompt = (
            f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\n"
            f"USER TASK:\n{prompt}\n\n"
            f"Return valid JSON only matching the requested schema."
        )

    url = f"{host}/api/generate"
    payload = {
        "model": model_name,
        "prompt": combined_prompt,
        "images": [image_b64],
        "format": "json",
        "stream": False,
    }
    if system_instruction:
        payload["system"] = system_instruction

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.Timeout as e:
        raise TimeoutError(f"Ollama local inference timed out after {timeout}s: {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"Failed to connect to local Ollama server at {host}: {e}") from e

    if resp.status_code != 200:
        raise RuntimeError(f"Ollama API HTTP {resp.status_code}: {resp.text}")

    resp_json = resp.json()
    raw_content = resp_json.get("response", "")
    parsed_json = extract_json_from_text(raw_content)

    return {
        "data": parsed_json,
        "raw_text": raw_content,
        "model_used": model_name,
        "provider_used": "ollama_fallback",
    }


def get_vision_completion(
    prompt: str,
    image_url: str,
    system_instruction: Optional[str] = None,
    response_schema: Optional[dict] = None,
    force_fallback: bool = False,
) -> VisionCompletionResult:
    """
    Unified entry point for vision completions:
    1. Attempts primary cloud provider (Gemini).
    2. Catches quota/rate-limit errors (429/RESOURCE_EXHAUSTED), timeouts,
       connection errors, and missing/invalid credentials.
    3. Seamlessly falls back to local Ollama vision model (llava).
    4. Sets provider_used: "gemini" or "ollama_fallback".
    """
    primary_error: Optional[str] = None
    force = force_fallback or os.getenv("LLM_FORCE_OLLAMA_FALLBACK", "").lower() in ("1", "true", "yes")

    if not force:
        try:
            res = call_gemini_vision(
                prompt=prompt,
                image_url=image_url,
                system_instruction=system_instruction,
                response_schema=response_schema,
            )
            return VisionCompletionResult(
                data=res["data"],
                provider_used=res["provider_used"],
                model_used=res["model_used"],
                raw_text=res.get("raw_text", ""),
                error_reason=None,
            )
        except Exception as e:
            if "couldn't read this image" in str(e).lower():
                raise
            primary_error = f"{type(e).__name__}: {e}"
            logger.warning(
                "[LLM Provider] Primary provider (Gemini) failed: %s. Falling back to local Ollama.",
                primary_error,
            )
    else:
        primary_error = "Fallback forced by test/configuration."

    # Fallback to local Ollama
    try:
        res = call_ollama_vision(
            prompt=prompt,
            image_url=image_url,
            system_instruction=system_instruction,
        )
        logger.info(
            "[LLM Provider] Fallback succeeded via local Ollama (%s).",
            res.get("model_used", "unknown"),
        )
        return VisionCompletionResult(
            data=res["data"],
            provider_used="ollama_fallback",
            model_used=res.get("model_used", OLLAMA_DEFAULT_VISION_MODEL),
            raw_text=res.get("raw_text", ""),
            error_reason=primary_error,
        )
    except Exception as ollama_err:
        logger.error(
            "[LLM Provider] Local Ollama fallback failed: %s (Primary error: %s)",
            ollama_err,
            primary_error,
        )
        raise RuntimeError(
            f"Vision completion failed across both primary provider and local Ollama fallback. "
            f"Primary error: {primary_error}; Ollama error: {ollama_err}"
        ) from ollama_err


class ChatCompletionResult:
    """Standardized result returned by text/chat LLM provider abstraction."""

    def __init__(
        self,
        content: str,
        provider_used: str,
        model_used: str,
        error_reason: Optional[str] = None,
    ):
        self.content = content
        self.provider_used = provider_used  # "gemini" or "ollama_fallback"
        self.model_used = model_used
        self.error_reason = error_reason

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "error_reason": self.error_reason,
        }


def call_gemini_chat(
    prompt: str,
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
    client: Optional[Any] = None,
) -> dict:
    """Invoke primary Gemini chat / text model."""
    if client is None:
        try:
            import app.services.vision_service as vs_mod
            client_getter = getattr(vs_mod, "_get_client", _get_default_client)
            client = client_getter()
        except Exception:
            client = _get_default_client()

    model_name = model or os.getenv("GEMINI_CHAT_MODEL") or os.getenv("GEMINI_VISION_MODEL", DEFAULT_PRIMARY_MODEL)

    from google.genai import types

    config_kwargs: dict[str, Any] = {}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    response = client.models.generate_content(
        model=model_name,
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
    )

    content = getattr(response, "text", "") or ""
    return {
        "content": content,
        "model_used": model_name,
        "provider_used": "gemini",
    }


def call_ollama_chat(
    prompt: str,
    system_instruction: Optional[str] = None,
    timeout_sec: float = 60.0,
    model: Optional[str] = None,
    host: Optional[str] = None,
) -> dict:
    """Invoke local Ollama text/chat endpoint via HTTP POST."""
    host = (host or os.getenv("OLLAMA_HOST", OLLAMA_DEFAULT_HOST)).rstrip("/")
    model_name = (
        model
        or os.getenv("OLLAMA_CHAT_MODEL")
        or os.getenv("OLLAMA_VISION_MODEL", OLLAMA_DEFAULT_VISION_MODEL)
    )
    timeout = float(os.getenv("OLLAMA_TIMEOUT_SEC", str(timeout_sec)))

    combined_prompt = prompt
    if system_instruction:
        combined_prompt = f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER REQUEST:\n{prompt}"

    url = f"{host}/api/generate"
    payload = {
        "model": model_name,
        "prompt": combined_prompt,
        "stream": False,
    }
    if system_instruction:
        payload["system"] = system_instruction

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.Timeout as e:
        raise TimeoutError(f"Ollama local chat inference timed out after {timeout}s: {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"Failed to connect to local Ollama server at {host}: {e}") from e

    if resp.status_code != 200:
        raise RuntimeError(f"Ollama API HTTP {resp.status_code}: {resp.text}")

    resp_json = resp.json()
    raw_content = resp_json.get("response", "")

    return {
        "content": raw_content,
        "model_used": model_name,
        "provider_used": "ollama_fallback",
    }


def get_chat_completion(
    prompt: str,
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
    force_fallback: bool = False,
) -> ChatCompletionResult:
    """
    Unified entry point for text/chat completions:
    1. Attempts primary cloud provider (Gemini).
    2. Catches quota/rate-limit errors (429/RESOURCE_EXHAUSTED), timeouts,
       connection errors, and missing/invalid credentials.
    3. Seamlessly falls back to local Ollama.
    4. Sets provider_used: "gemini" or "ollama_fallback".
    """
    primary_error: Optional[str] = None
    force = force_fallback or os.getenv("LLM_FORCE_OLLAMA_FALLBACK", "").lower() in ("1", "true", "yes")

    if not force:
        try:
            res = call_gemini_chat(
                prompt=prompt,
                system_instruction=system_instruction,
                model=model,
            )
            return ChatCompletionResult(
                content=res["content"],
                provider_used=res["provider_used"],
                model_used=res["model_used"],
                error_reason=None,
            )
        except Exception as e:
            primary_error = f"{type(e).__name__}: {e}"
            logger.warning(
                "[LLM Provider] Primary provider (Gemini chat) failed: %s. Falling back to local Ollama.",
                primary_error,
            )
    else:
        primary_error = "Fallback forced by test/configuration."

    # Fallback to local Ollama
    try:
        res = call_ollama_chat(
            prompt=prompt,
            system_instruction=system_instruction,
            model=model,
        )
        logger.info(
            "[LLM Provider] Chat fallback succeeded via local Ollama (%s).",
            res.get("model_used", "unknown"),
        )
        return ChatCompletionResult(
            content=res["content"],
            provider_used="ollama_fallback",
            model_used=res.get("model_used", OLLAMA_DEFAULT_VISION_MODEL),
            error_reason=primary_error,
        )
    except Exception as ollama_err:
        logger.error(
            "[LLM Provider] Local Ollama chat fallback failed: %s (Primary error: %s)",
            ollama_err,
            primary_error,
        )
        raise RuntimeError(
            f"Chat completion failed across both primary provider and local Ollama fallback. "
            f"Primary error: {primary_error}; Ollama error: {ollama_err}"
        ) from ollama_err

