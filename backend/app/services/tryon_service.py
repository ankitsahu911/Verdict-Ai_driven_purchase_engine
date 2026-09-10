import logging
import os
import time
from pathlib import Path

from typing import Any
import requests
from dotenv import load_dotenv

from app.services.vision_service import analyze_fit

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)


class TryOnServiceError(RuntimeError):
    """Base error for virtual try-on agent failures."""
    pass


class TryOnTimeoutError(TryOnServiceError):
    """Raised when YouCam API connection or polling times out."""
    pass


class TryOnConnectionError(TryOnServiceError):
    """Raised on network connectivity, DNS, or socket connection errors."""
    pass


DEFAULT_FALLBACK_FIT_TIGHTNESS = "regular"
DEFAULT_FALLBACK_SILHOUETTE = "relaxed"
DEFAULT_TRYON_PLACEHOLDER_URL = (
    "https://placehold.co/600x800/e2e8f0/475569.png?text=Virtual+Try-On+Unavailable"
)


def build_tryon_fallback(
    item: Any,
    error_reason: str = "YouCam service unreachable",
) -> dict:
    """
    Fallback hierarchy for Try-On failures (M33):
    2a. If this item has ANY previously-cached render (from M32), even a stale one,
        use it rather than failing outright.
    2b. If there's no cached render at all, use a generic placeholder image and
        neutral default fit values (fit_tightness: 'regular', silhouette: 'relaxed').
    3. In EITHER fallback case, set tryon_degraded: True.
    """
    cached_render = getattr(item, "tryon_render_url", None)
    if cached_render and isinstance(cached_render, str):
        logger.warning(
            "[TryOn Degraded] Fallback to stale cached render for item %s due to: %s",
            getattr(item, "id", "unknown"),
            error_reason,
        )
        return {
            "render_url": cached_render,
            "fit_tightness": getattr(item, "fit_tightness", None) or DEFAULT_FALLBACK_FIT_TIGHTNESS,
            "silhouette": getattr(item, "silhouette", None) or DEFAULT_FALLBACK_SILHOUETTE,
            "notes": f"Degraded fallback: using stale cached render ({error_reason}).",
            "cached": True,
            "tryon_degraded": True,
        }

    placeholder_url = (
        getattr(item, "cloudinary_url", None)
        or DEFAULT_TRYON_PLACEHOLDER_URL
    )
    logger.warning(
        "[TryOn Degraded] Fallback to placeholder render and neutral fit signals for item %s due to: %s",
        getattr(item, "id", "unknown"),
        error_reason,
    )
    return {
        "render_url": placeholder_url,
        "fit_tightness": DEFAULT_FALLBACK_FIT_TIGHTNESS,
        "silhouette": DEFAULT_FALLBACK_SILHOUETTE,
        "notes": f"Degraded fallback: using placeholder render and neutral fit ({error_reason}).",
        "cached": False,
        "tryon_degraded": True,
    }


BASE_URL_V3 = "https://yce-api-01.makeupar.com/s2s/v2.0/task/cloth-v3"
POLL_INTERVAL_SEC = 3
MAX_POLL_SEC = 120


def generate_tryon(
    garment_url: str,
    user_photo_url: str | None = None,
    garment_category: str | None = None,
) -> dict:
    if not garment_url:
        raise TryOnServiceError("No garment image URL provided.")

    api_key = os.getenv("YOUCAM_API_KEY")
    if not api_key:
        raise TryOnServiceError(
            "YOUCAM_API_KEY is not set. Set it in your .env file."
        )

    resolved_user_url = user_photo_url or os.getenv("YOUCAM_SRC_URL")
    if not resolved_user_url:
        raise TryOnServiceError(
            "No model/user photo URL provided. Set YOUCAM_SRC_URL in .env or pass user_photo_url."
        )

    resolved_category = (
        garment_category or os.getenv("YOUCAM_GARMENT_CATEGORY") or "full_body"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "garment_category": resolved_category,
        "src_file_url": resolved_user_url,
        "ref_file_url": garment_url,
    }

    timeout = float(os.getenv("YOUCAM_TIMEOUT_SEC", "15.0"))
    poll_timeout = float(os.getenv("YOUCAM_POLL_TIMEOUT_SEC", "8.0"))

    try:
        resp = requests.post(BASE_URL_V3, json=payload, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout as e:
        raise TryOnTimeoutError(f"YouCam API connection timed out after {timeout}s: {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise TryOnConnectionError(f"Failed to connect to YouCam API: {e}") from e
    except requests.exceptions.RequestException as e:
        raise TryOnServiceError(f"Failed to connect to YouCam API: {e}") from e
    except Exception as e:
        raise TryOnServiceError(f"Failed to connect to YouCam API: {e}") from e

    if resp.status_code != 200:
        raise TryOnServiceError(
            f"YouCam API HTTP error {resp.status_code}: {resp.text}"
        )

    try:
        task_data = resp.json()
    except ValueError as e:
        raise TryOnServiceError(f"Invalid JSON from YouCam API: {resp.text}") from e

    if task_data.get("status") != 200:
        raise TryOnServiceError(f"YouCam task creation failed: {task_data}")

    task_id = task_data.get("data", {}).get("task_id")
    if not task_id:
        raise TryOnServiceError("YouCam response missing task_id.")

    poll_url = f"{BASE_URL_V3}/{task_id}"
    start_time = time.monotonic()
    result_data = None

    while True:
        elapsed = time.monotonic() - start_time
        if elapsed > MAX_POLL_SEC:
            raise TryOnTimeoutError(
                f"YouCam try-on task timed out after {MAX_POLL_SEC} seconds."
            )

        try:
            r = requests.get(poll_url, headers=headers, timeout=poll_timeout)
            r.raise_for_status()
            body = r.json()
        except requests.exceptions.Timeout as e:
            logger.warning("Polling YouCam task %s timeout: %s", task_id, e)
            time.sleep(POLL_INTERVAL_SEC)
            continue
        except requests.exceptions.ConnectionError as e:
            logger.warning("Polling YouCam task %s connection error: %s", task_id, e)
            time.sleep(POLL_INTERVAL_SEC)
            continue
        except Exception as e:
            logger.warning("Polling YouCam task %s error: %s", task_id, e)
            time.sleep(POLL_INTERVAL_SEC)
            continue

        status = body.get("data", {}).get("task_status")
        if status == "success":
            result_data = body.get("data", {})
            break
        elif status == "error":
            err_msg = body.get("data", {}).get("error", "unknown error")
            raise TryOnServiceError(f"YouCam task failed: {err_msg}")

        time.sleep(POLL_INTERVAL_SEC)

    render_url = result_data.get("results", {}).get("url")
    if not render_url:
        raise TryOnServiceError("YouCam result missing render image URL.")

    fit_data = None
    try:
        fit_data = analyze_fit(render_url)
    except Exception as e:
        logger.warning(
            "Fit analysis failed for render URL %s (returning render with null fit fields): %s",
            render_url,
            e,
        )

    return {
        "render_url": render_url,
        "fit_tightness": fit_data["fit_tightness"] if fit_data else None,
        "silhouette": fit_data["silhouette"] if fit_data else None,
        "notes": fit_data["notes"] if fit_data else None,
    }
