"""Session authentication and CSRF checks shared by protected routes."""
from dataclasses import dataclass
from datetime import datetime
import os
import re
import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie
from sqlalchemy.exc import SQLAlchemyError

from persistence import auth_store
from persistence.database import DatabaseUnavailable

COOKIE_NAME = 'patent_session'
cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)
DEFAULT_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000'


def allowed_origins():
    return [origin.strip().rstrip('/') for origin in os.getenv('APP_ORIGINS', DEFAULT_ORIGINS).split(',') if origin.strip() and origin.strip() != '*']


def check_origin(request: Request):
    origin = request.headers.get('origin')
    if origin is not None and origin not in allowed_origins():
        raise HTTPException(403, 'Request origin is not allowed.')


def require_json_client(request: Request):
    check_origin(request)
    if request.headers.get('x-requested-with') != 'patent-client':
        raise HTTPException(403, 'Use the application to submit this request.')


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    display_name: str
    csrf_token: str
    expires_at: datetime


def require_user(request: Request, token: str | None = Depends(cookie_scheme)) -> Principal:
    if not token or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise HTTPException(401, 'Sign in to continue.')
    try:
        user = auth_store.read_session(token)
    except (DatabaseUnavailable, SQLAlchemyError) as exc:
        raise HTTPException(503, 'Account storage is unavailable. Try again shortly.') from exc
    if not user:
        raise HTTPException(401, 'Your session has expired. Sign in again.')
    csrf = auth_store.csrf_token(token)
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        check_origin(request)
        if not secrets.compare_digest(request.headers.get('x-csrf-token', ''), csrf):
            raise HTTPException(403, 'Security token is missing or invalid. Refresh and try again.')
    return Principal(**user, csrf_token=csrf)


def owned_run_input(req, user: Principal):
    """Validate embedded IDs too, and use server snapshots for saved-run work."""
    from persistence import analysis_store as store
    nested = req.pipeline_result or {}
    nested_run = nested.get('run_id')
    if req.run_id and nested_run and req.run_id != nested_run:
        raise HTTPException(422, 'Run identifiers do not match.')
    run_id = req.run_id or nested_run
    try:
        if run_id:
            saved = store.get_owned_run(run_id, owner_user_id=user.user_id)
            if not saved:
                raise HTTPException(404, 'Analysis run not found.')
            if nested.get('case_id') and nested['case_id'] != saved['case_id']:
                raise HTTPException(404, 'Analysis run not found.')
            req.run_id = run_id
            req.idea = saved['idea_text']
            req.pipeline_result = saved['pipeline_result']
            if hasattr(req, 'evaluation_result'):
                req.evaluation_result = saved['evaluation_result']
        elif nested.get('case_id') and not store.get_case(nested['case_id'], owner_user_id=user.user_id):
            raise HTTPException(404, 'Analysis case not found.')
    except (DatabaseUnavailable, SQLAlchemyError) as exc:
        raise HTTPException(503, 'Saved analysis storage is unavailable.') from exc
