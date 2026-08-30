import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

API_KEY = os.getenv("YOUCAM_API_KEY")
if not API_KEY:
    print("ERROR: YOUCAM_API_KEY is not set in .env")
    sys.exit(1)

BASE_URL = "https://yce-api-01.makeupar.com"
SRC_IMAGE_URL = os.getenv("YOUCAM_SRC_URL")
REF_IMAGE_URL = os.getenv("YOUCAM_REF_URL")
GARMENT_CATEGORY = os.getenv("YOUCAM_GARMENT_CATEGORY", "full_body")

SRC_IMAGE_PATH = None
REF_IMAGE_PATH = None

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
POLL_INTERVAL_SEC = 3
MAX_POLL_SEC = 120

OUTPUT_FILE = Path(__file__).resolve().parent / "last_render_url.txt"
BASE_URL_V3 = f"{BASE_URL}/s2s/v2.0/task/cloth-v3"
FILE_API_URL = f"{BASE_URL}/s2s/v2.0/file"

print("\n=== Step 0: Auth check ===")
resp = requests.get(
    f"{BASE_URL_V3}/placeholder-nonexistent",
    headers=HEADERS,
    timeout=10,
)
if resp.status_code in (401, 403):
    print(f"  FAILED — API key rejected ({resp.status_code})")
    print(f"  Response: {resp.text}")
    sys.exit(1)
elif resp.status_code == 404:
    print("  OK — API key accepted (got 404 on fake resource as expected)")
else:
    print(f"  OK — API key accepted (status {resp.status_code})")

print("\n=== Step 1: Upload images (if needed) ===")

def upload_file(file_path: str) -> str:
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        print(f"  SKIP — file not found: {file_path}")
        return None
    file_size = file_path_obj.stat().st_size
    file_name = file_path_obj.name
    ext = file_path_obj.suffix.lower()
    content_type = "image/png" if ext == ".png" else "image/jpeg"

    payload = {
        "files": [
            {
                "content_type": content_type,
                "file_name": file_name,
                "file_size": file_size,
            }
        ]
    }
    r = requests.post(FILE_API_URL, json=payload, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()["data"]["files"][0]
    file_id = data["file_id"]
    upload_info = data["requests"][0]

    upload_url = upload_info["url"]
    upload_headers = upload_info["headers"]
    with open(file_path, "rb") as f:
        ur = requests.put(upload_url, data=f, headers=upload_headers, timeout=60)
    ur.raise_for_status()

    print(f"  Uploaded {file_name} → file_id={file_id[:40]}…")
    return file_id

src_file_id = None
ref_file_id = None

if SRC_IMAGE_PATH:
    src_file_id = upload_file(SRC_IMAGE_PATH)

if REF_IMAGE_PATH:
    ref_file_id = upload_file(REF_IMAGE_PATH)

task_payload = {}
task_payload["garment_category"] = GARMENT_CATEGORY

if src_file_id:
    task_payload["src_file_id"] = src_file_id
elif SRC_IMAGE_URL:
    task_payload["src_file_url"] = SRC_IMAGE_URL

if ref_file_id:
    task_payload["ref_file_id"] = ref_file_id
elif REF_IMAGE_URL:
    task_payload["ref_file_url"] = REF_IMAGE_URL

if "src_file_url" not in task_payload and "src_file_id" not in task_payload:
    print("\n  WARNING: No source image provided — task will likely fail.")
    print("  Set YOUCAM_SRC_URL and YOUCAM_REF_URL in .env, or define")
    print("  SRC_IMAGE_PATH / REF_IMAGE_PATH at the top of this script.\n")

print("\n=== Step 2: Create AI task ===")
print(f"  Payload: {json.dumps(task_payload, indent=4)}")

resp = requests.post(BASE_URL_V3, json=task_payload, headers=HEADERS, timeout=30)
if resp.status_code != 200:
    print(f"  FAILED — HTTP {resp.status_code}")
    print(f"  Response: {resp.text}")
    sys.exit(1)

task_data = resp.json()
if task_data.get("status") != 200:
    print(f"  FAILED — API error: {task_data}")
    sys.exit(1)

task_id = task_data["data"]["task_id"]
print(f"  Task created: {task_id}")

print(f"\n=== Step 3: Poll for result (polling every {POLL_INTERVAL_SEC}s) ===")
poll_url = f"{BASE_URL_V3}/{task_id}"

start = time.monotonic()
result_data = None

while True:
    elapsed = time.monotonic() - start
    if elapsed > MAX_POLL_SEC:
        print(f"  TIMEOUT after {MAX_POLL_SEC}s — aborting")
        sys.exit(1)

    r = requests.get(poll_url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    body = r.json()

    status = body.get("data", {}).get("task_status")
    print(f"  [{elapsed:5.1f}s] task_status={status}")

    if status == "success":
        result_data = body["data"]
        break
    elif status == "error":
        error_info = body.get("data", {}).get("error", "unknown error")
        print(f"\n  FAILED — task error: {error_info}")
        print(f"  Full response: {json.dumps(body, indent=2)}")
        sys.exit(1)

    time.sleep(POLL_INTERVAL_SEC)

print("\n=== Step 4: Result ===")
render_url = result_data.get("results", {}).get("url")
if not render_url:
    print(f"  No render URL in response: {json.dumps(result_data, indent=2)}")
    sys.exit(1)

print(f"  Render URL: {render_url}")

OUTPUT_FILE.write_text(render_url + "\n")
print(f"  Saved to: {OUTPUT_FILE}")

print("\nYouCam test PASSED — open the URL above in a browser to verify the try-on.")
