import json
import os

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

security = HTTPBearer()

_credential_source: str | None = None


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
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    _get_firebase_app()
    token = credentials.credentials
    try:
        decoded = firebase_auth.verify_id_token(token)
        return {"uid": decoded["uid"], "email": decoded.get("email", "")}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        )
