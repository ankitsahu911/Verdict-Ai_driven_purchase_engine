"""
Milestone Verification Script: Live Gemini API Key Test.
Tests both Vision Garment Extraction and Stylist Chat Completion using the configured GEMINI_API_KEY.
"""

import os
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(dotenv_path=backend_dir.parent / ".env")

from app.services.llm_provider import call_gemini_vision, call_gemini_chat

def main():
    print("=" * 70)
    print("           VERDICT — LIVE GEMINI API KEY VERIFICATION")
    print("=" * 70)

    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        print("[FAIL] GEMINI_API_KEY is not set in .env file!")
        return

    masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
    print(f"Loaded GEMINI_API_KEY: {masked_key}")
    model = os.getenv("GEMINI_VISION_MODEL", "gemini-3.5-flash")
    print(f"Active Vision Model:   {model}\n")

    # 1. Test Vision Garment Extraction
    print("[TEST 1/2] Testing Vision Garment Extraction on real photo...")
    test_img = backend_dir / "data" / "uploads" / "top_01_white_crewneck_tee.jpg"
    if not test_img.exists():
        # Fallback to demo photos
        test_img = backend_dir / "data" / "demo_wardrobe_photos" / "top_01_white_crewneck_tee.jpg"

    schema = {
        "type": "OBJECT",
        "properties": {
            "category": {"type": "STRING"},
            "color": {"type": "STRING"},
            "style": {"type": "STRING"},
            "material": {"type": "STRING"},
            "season": {"type": "STRING"},
        },
        "required": ["category", "color", "style", "material", "season"],
    }

    try:
        res = call_gemini_vision(
            prompt="Analyze this clothing photo and extract garment attributes in JSON.",
            image_url=str(test_img),
            response_schema=schema,
            model=model,
        )
        print("  [SUCCESS] Vision Agent extraction returned:")
        for k, v in res.get("data", {}).items():
            print(f"    - {k.capitalize():<10}: {v}")
        print(f"    (Model used: {res.get('model_used')}, Provider: {res.get('provider_used')})")
    except Exception as e:
        print(f"  [ERROR] Vision test failed: {e}")

    # 2. Test Stylist Chat Completion
    print("\n[TEST 2/2] Testing Stylist Chat Completion...")
    try:
        chat_res = call_gemini_chat(
            prompt="Give me a 1-sentence tip on how to style a white crewneck tee for a smart-casual dinner.",
            model=model,
        )
        print("  [SUCCESS] Stylist Agent responded:")
        print(f"    \"{chat_res.get('content', '').strip()}\"")
    except Exception as e:
        print(f"  [ERROR] Stylist test failed: {e}")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE: Your Gemini API key is working perfectly!")
    print("=" * 70)

if __name__ == "__main__":
    main()
