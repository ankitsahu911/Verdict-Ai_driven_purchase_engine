from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_current_user
from app.routers import wardrobe

app = FastAPI(title="Verdict Backend", version="0.1.0")

app.include_router(wardrobe.router)

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
async def api_me(user: dict = Depends(get_current_user)):
    return user
