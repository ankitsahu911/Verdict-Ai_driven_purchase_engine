import base64
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
API_KEY = os.getenv("CLOUDINARY_API_KEY")
API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if not all([CLOUD_NAME, API_KEY, API_SECRET]):
    print("ERROR: One or more Cloudinary env vars are missing.")
    print("  Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")
    sys.exit(1)

cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET,
    secure=True,
)

MINIMAL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

with tempfile.NamedTemporaryFile(suffix=".png", delete=False, mode="wb") as f:
    f.write(base64.b64decode(MINIMAL_PNG_BASE64))
    tmp_path = f.name

print(f"Uploading test image from {tmp_path} …")
result = cloudinary.uploader.upload(tmp_path, public_id="verdict_test_pixel")

os.unlink(tmp_path)

secure_url = result.get("secure_url")
public_id = result.get("public_id")

print(f"  Public ID:   {public_id}")
print(f"  Secure URL:  {secure_url}")
print("\nCloudinary test PASSED")
