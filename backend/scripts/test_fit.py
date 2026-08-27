"""
Test script for Fit Analysis and Try-On Agent (MILESTONE 11).

Tests:
1. Standalone `analyze_fit(render_image_url)` using Gemini vision.
2. End-to-end `generate_tryon(garment_url)` incorporating YouCam try-on + fit analysis.

Usage:
    python scripts/test_fit.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from app.services.tryon_service import generate_tryon
from app.services.vision_service import VisionServiceError, analyze_fit

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")


def test_fit_analysis():
    print("\n=== 1. Testing Standalone analyze_fit ===")
    sample_render_url = (
        "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f"
    )
    print(f"Analyzing sample render URL: {sample_render_url}")

    try:
        res = analyze_fit(sample_render_url)
        print("Result from analyze_fit:")
        print(json.dumps(res, indent=2))
        assert "fit_tightness" in res and res["fit_tightness"] in {
            "tight",
            "regular",
            "loose",
            "oversized",
        }
        assert "silhouette" in res and res["silhouette"] in {
            "slim",
            "tailored",
            "relaxed",
            "boxy",
        }
        assert "notes" in res
        print("Standalone analyze_fit PASSED.")
    except VisionServiceError as e:
        print(f"FAILED analyze_fit: {e}")
        return False
    return True


def test_e2e_tryon_and_fit():
    print("\n=== 2. Testing End-to-End YouCam Try-On + Fit Analysis ===")
    api_key = os.getenv("YOUCAM_API_KEY")
    garment_url = os.getenv("YOUCAM_REF_URL")
    model_url = os.getenv("YOUCAM_SRC_URL")

    if not api_key:
        print("SKIP: YOUCAM_API_KEY is not set.")
        return True

    if not garment_url or not model_url:
        print("SKIP: YOUCAM_REF_URL or YOUCAM_SRC_URL is not set.")
        return True

    print(f"Garment URL: {garment_url}")
    print(f"Model URL:   {model_url}")

    try:
        result = generate_tryon(garment_url=garment_url, user_photo_url=model_url)
        print("Combined Try-On + Fit Result:")
        print(json.dumps(result, indent=2))

        assert "render_url" in result and result["render_url"].startswith("http")
        assert "fit_tightness" in result
        assert "silhouette" in result
        assert "notes" in result
        print("End-to-End Try-On + Fit Analysis PASSED.")
    except Exception as e:
        print(f"FAILED e2e try-on: {e}")
        return False
    return True


if __name__ == "__main__":
    ok1 = test_fit_analysis()
    ok2 = test_e2e_tryon_and_fit()
    if ok1 and ok2:
        print("\nAll Milestone 11 tests PASSED!")
        sys.exit(0)
    else:
        print("\nSome tests FAILED.")
        sys.exit(1)
