"""
Manual test harness for the Vision Agent (MILESTONE 7).

Runs attribute extraction across ~10 varied garment photos and prints
category/color/pattern so you can eyeball correctness. "Correct" here is a
human judgment call — the goal is >= 8/10 right.

Usage:
  python scripts/test_vision.py              # analyze the built-in sample set
  python scripts/test_vision.py <url> ...    # analyze your own photo URLs

To test the full endpoint (auth + DB write) after uploading an item:
  curl -X POST http://localhost:8000/api/wardrobe/<item_id>/analyze \
       -H "Authorization: Bearer <firebase-id-token>"
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.vision_service import VisionServiceError, analyze_image  # noqa: E402

# Free-tier Flash models cap around 10 RPM — pace the batch to avoid 429s.
DELAY_BETWEEN_PHOTOS = 6.5

SAMPLE_PHOTOS = [
    ("white t-shirt", "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab"),
    ("khaki jacket", "https://images.unsplash.com/photo-1591047139829-d91aecb6caea"),
    ("denim jacket (on person)", "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1"),
    ("black dress", "https://images.unsplash.com/photo-1539533018447-63fcce2678e3"),
    ("leather jacket", "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446"),
    ("blue jeans", "https://images.unsplash.com/photo-1560243563-062bfc001d68"),
    ("t-shirt on model", "https://images.unsplash.com/photo-1541099649105-f69ad21f3246"),
    ("coat / fashion look", "https://images.unsplash.com/photo-1445205170230-053b83016050"),
    ("floral dress", "https://images.unsplash.com/photo-1490481651871-ab68de25d43d"),
    ("striped shirts on rack", "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633"),
]


def main() -> int:
    if len(sys.argv) > 1:
        jobs = [(f"custom-{i}", url) for i, url in enumerate(sys.argv[1:])]
    else:
        jobs = SAMPLE_PHOTOS

    print(f"Analyzing {len(jobs)} photo(s) ...\n")

    header = f"{'#':<3} {'label':<22} {'category':<14} {'color':<14} {'pattern':<12}"
    print(header)
    print("-" * len(header))

    errors = 0
    for i, (label, url) in enumerate(jobs, start=1):
        try:
            result = analyze_image(url)
            print(
                f"{i:<3} {label[:22]:<22} {result['category'][:14]:<14} "
                f"{result['color'][:14]:<14} {result['pattern'][:12]:<12}"
            )
        except VisionServiceError as e:
            errors += 1
            print(f"{i:<3} {label[:22]:<22} ERROR: {e}")
        if i < len(jobs):
            time.sleep(DELAY_BETWEEN_PHOTOS)

    print("-" * len(header))
    print(f"\n{len(jobs) - errors}/{len(jobs)} analyzed OK ({errors} errors).")
    print("Eyeball the rows above — you're looking for >= 8/10 sensible answers.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
