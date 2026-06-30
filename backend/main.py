"""
backend/main.py

FastAPI application entry point. This is the thin API layer —
all actual ML logic lives in ml_core/ and is called from here.

Run locally:
    uvicorn backend.main:app --reload --port 8000

Or from the project root:
    cd metalearn && uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import sessions, users, dashboard
from backend.core.config import settings

app = FastAPI(
    title="MetaLearn API",
    version="0.1.0",
    description="AI-powered metacognitive learning OS",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
