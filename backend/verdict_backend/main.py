from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.routers import candidates, opportunity_cost, stylist, tryon, wardrobe, what_if
from app.routers.wardrobe import get_or_create_user

app = FastAPI(title="Verdict Backend", version="0.1.0")

app.include_router(wardrobe.router)
app.include_router(tryon.router)
app.include_router(candidates.router)
app.include_router(what_if.router)
app.include_router(opportunity_cost.router)
app.include_router(stylist.router)

from pathlib import Path
from fastapi.staticfiles import StaticFiles

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "verdict-backend"}


@app.get("/api/me")
async def api_me(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_or_create_user(db, user["uid"], user["email"])
    return {
        **user,
        "id": owner.id,
        "model_photo_url": owner.model_photo_url,
    }


class ModelPhotoUpdateRequest(BaseModel):
    model_photo_url: str


@app.patch("/api/me/model-photo")
async def update_user_model_photo(
    payload: ModelPhotoUpdateRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_or_create_user(db, user["uid"], user["email"])
    owner.model_photo_url = payload.model_photo_url.strip()
    db.commit()
    db.refresh(owner)
    return {
        "user_id": owner.id,
        "model_photo_url": owner.model_photo_url,
    }

