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
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
from api.auth import allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Requested-With"],
)


@app.exception_handler(RequestValidationError)
async def safe_validation_errors(request, exc):
    # Pydantic's default error includes the rejected input (possibly a password).
    errors = [{key: error[key] for key in ('loc', 'msg', 'type') if key in error} for error in exc.errors()]
    return JSONResponse(status_code=422, content={'detail': errors}, headers={'Cache-Control': 'no-store'})


@app.middleware('http')
async def private_response_cache_policy(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response

# ── Routers ───────────────────────────────────────────────────────────────────
from api.routers import pipeline as pipeline_router    # noqa: E402
from api.routers import kg as kg_router                # noqa: E402
from api.routers import evaluate as evaluate_router    # noqa: E402
from api.routers import improve as improve_router      # noqa: E402
from api.routers import cases as cases_router          # noqa: E402
from api.routers import auth as auth_router

app.include_router(pipeline_router.router, prefix="/api")
app.include_router(kg_router.router, prefix="/api")
app.include_router(evaluate_router.router, prefix="/api")
app.include_router(improve_router.router, prefix="/api")
app.include_router(cases_router.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")



@app.get("/api/health", tags=["health"])
async def health_check():
    """Liveness probe."""
    return {"status": "ok", "service": "Patent Intelligence API", "version": "1.0.0"}
