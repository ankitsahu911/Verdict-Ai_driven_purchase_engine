import json
import os

import firebase_admin
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

security = HTTPBearer(auto_error=False)

_credential_source: str | None = None

DEMO_USER = {
    "uid": "demo_user_wardrobe",
    "email": "demo@verdict.engine",
    "name": "Verdict Demo Presenter",
}

DEV_USER = {
    "uid": "dev_user_local",
    "email": "dev@verdict.engine",
    "name": "Local Dev User",
}


def _get_firebase_app() -> firebase_admin.App:
    """Lazy-init Firebase Admin SDK from env vars."""
    global _credential_source
    if firebase_admin._apps:
        return list(firebase_admin._apps.values())[0]

    json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    json_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")

    if json_str:
        cred = credentials.Certificate(json.loads(json_str))
        _credential_source = "FIREBASE_SERVICE_ACCOUNT_JSON"
    elif json_path:
        cred = credentials.Certificate(json_path)
        _credential_source = f"file ({json_path})"
    else:
        raise RuntimeError(
            "Set FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH in .env"
        )

    return firebase_admin.initialize_app(cred)


def get_current_user(
    request: Request = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    # 1. Check for explicit Demo Account indicators (Header or Token)
    if request is not None:
        user_header = request.headers.get("x-verdict-user", "").strip().lower()
        if user_header in ("demo", "demo_user", "demo_user_wardrobe"):
            return DEMO_USER

    if credentials and credentials.credentials in ("demo-token", "demo", "demo_user_wardrobe"):
        return DEMO_USER

    json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    json_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")

    # 2. If Firebase credentials are not configured or dev bypass is enabled, use DEV_USER (or DEMO_USER if requested)
    if not json_str and not json_path:
        if request is not None and request.headers.get("x-verdict-user") == "demo":
            return DEMO_USER
        return DEV_USER

    if credentials is None:
        if os.getenv("DEV_AUTH_BYPASS", "true").lower() in ("true", "1"):
            return DEV_USER
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    try:
        _get_firebase_app()
        token = credentials.credentials
        decoded = firebase_auth.verify_id_token(token)
        uid = decoded["uid"]
        email = decoded.get("email", "")
        if email == "demo@verdict.engine" or uid == "demo_user_wardrobe":
            return DEMO_USER
        return {"uid": uid, "email": email}
    except Exception as e:
        if os.getenv("DEV_AUTH_BYPASS", "true").lower() in ("true", "1"):
            return DEV_USER
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        )
