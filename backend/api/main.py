"""
FastAPI application entry point.
Patent Intelligence Platform — REST API layer.

Run with:
    cd patent-kg/backend
    python run_api.py
    # or: uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Load .env before anything else ───────────────────────────────────────────
# Searches upward from backend/ — finds patent-kg/.env
_BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND_DIR.parent / ".env")   # patent-kg/.env

# ── Ensure backend/src/ is importable ────────────────────────────────────────
_SRC = _BACKEND_DIR / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load heavy resources on startup so first request is fast."""
    print("[startup] Loading FAISS index and SentenceTransformer model...")
    try:
        from integration.pipeline import _load_resources, _get_model
        _load_resources()
        _get_model()
        print("[startup] Pipeline resources loaded OK.")
    except Exception as exc:
        # Non-fatal — resources will be loaded lazily on first request
        print(f"[startup] Warning: could not pre-load pipeline resources: {exc}")
    yield
    print("[shutdown] API shutting down.")


app = FastAPI(
    title="Patent Intelligence Platform API",
    description="REST API powering the React frontend for the Graph-Enhanced Patent Intelligence Platform.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — allow Vite dev server ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from api.routers import pipeline as pipeline_router    # noqa: E402
from api.routers import kg as kg_router                # noqa: E402
from api.routers import evaluate as evaluate_router    # noqa: E402
from api.routers import improve as improve_router      # noqa: E402

app.include_router(pipeline_router.router, prefix="/api")
app.include_router(kg_router.router, prefix="/api")
app.include_router(evaluate_router.router, prefix="/api")
app.include_router(improve_router.router, prefix="/api")



@app.get("/api/health", tags=["health"])
async def health_check():
    """Liveness probe."""
    return {"status": "ok", "service": "Patent Intelligence API", "version": "1.0.0"}
