"""
Try-On Agent service (MILESTONES 10 + 11).

Orchestrates virtual try-on via YouCam API and immediately derives structured
fit signals (fit_tightness, silhouette, notes) via Gemini vision analysis.
"""

import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from app.services.vision_service import analyze_fit

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)


class TryOnServiceError(RuntimeError):
    """Raised when virtual try-on processing fails."""


BASE_URL_V3 = "https://yce-api-01.makeupar.com/s2s/v2.0/task/cloth-v3"
POLL_INTERVAL_SEC = 3
MAX_POLL_SEC = 120


def generate_tryon(
    garment_url: str,
    user_photo_url: str | None = None,
    garment_category: str | None = None,
) -> dict:
    """Generate virtual try-on render URL from YouCam and derive fit analysis.

    Returns:
        {
            "render_url": str,
            "fit_tightness": str | None,
            "silhouette": str | None,
            "notes": str | None,
        }

    If YouCam succeeds but fit analysis fails, returns render_url with null/empty fit fields.
    """
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

    logger.info("Initiating YouCam try-on task for garment: %s", garment_url)
    try:
        resp = requests.post(BASE_URL_V3, json=payload, headers=headers, timeout=30)
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

    logger.info("YouCam task created: %s. Polling for results...", task_id)
    poll_url = f"{BASE_URL_V3}/{task_id}"
    start_time = time.monotonic()
    result_data = None

    while True:
        elapsed = time.monotonic() - start_time
        if elapsed > MAX_POLL_SEC:
            raise TryOnServiceError(
                f"YouCam try-on task timed out after {MAX_POLL_SEC} seconds."
            )

        try:
            r = requests.get(poll_url, headers=headers, timeout=10)
            r.raise_for_status()
            body = r.json()
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

    logger.info("YouCam render URL generated successfully: %s", render_url)

    # Separate fit analysis pass on rendered image
    fit_data = None
    try:
        logger.info("Running fit analysis on render URL: %s", render_url)
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
