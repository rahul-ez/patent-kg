"""Email/password signup, revocable cookie sessions, current account and logout."""
import os
import secrets
from threading import BoundedSemaphore

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator
from pwdlib import PasswordHash, exceptions as password_errors
from sqlalchemy.exc import SQLAlchemyError

from api.auth import COOKIE_NAME, Principal, require_json_client, require_user
from persistence import auth_store
from persistence.database import DatabaseUnavailable

router = APIRouter(prefix='/auth', tags=['authentication'])
hasher = PasswordHash.recommended()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
hash_slots = BoundedSemaphore(4)


class Credentials(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return str(value).casefold()


class Registration(Credentials):
    display_name: str = Field(min_length=1, max_length=120)
    password: SecretStr = Field(min_length=15, max_length=128)

    @field_validator('display_name')
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError('Enter your name.')
        return value.strip()

    @field_validator('password')
    @classmethod
    def nonblank_password(cls, value):
        if not value.get_secret_value().strip():
            raise ValueError('Choose a password that is not only spaces.')
        return value


def throttle(request, email, action):
    # Do not trust client-supplied forwarding headers. Configure a trusted proxy
    # at deployment if the API is not directly reachable.
    ip = request.client.host if request.client else 'unknown'
    limits = [(f'{action}:ip:{ip}', 30 if action == 'login' else 10, 900 if action == 'login' else 3600),
              (f'{action}:email:{email}', 10, 900)]
    for key, limit, seconds in limits:
        if not auth_store.throttle(key, limit, seconds):
            raise HTTPException(429, 'Too many attempts. Try again later.', headers={'Retry-After': str(seconds)})


def session_response(request, response, user):
    hours = max(1, min(168, int(os.getenv('SESSION_HOURS', '12'))))
    token, expiry = auth_store.create_session(user['user_id'], hours, request.cookies.get(COOKIE_NAME))
    response.set_cookie(COOKIE_NAME, token, max_age=hours * 3600, path='/api', httponly=True,
                        secure=os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true', samesite='lax')
    response.headers['Cache-Control'] = 'no-store'
    return {'user': {key: user[key] for key in ('user_id', 'email', 'display_name')},
            'csrf_token': auth_store.csrf_token(token), 'expires_at': expiry}


@router.post('/signup', status_code=201, dependencies=[Depends(require_json_client)])
def signup(payload: Registration, request: Request, response: Response):
    try:
        throttle(request, payload.email, 'signup')
        if not hash_slots.acquire(blocking=False):
            raise HTTPException(429, 'Sign-in service is busy. Try again shortly.')
        try:
            password_hash = hasher.hash(payload.password.get_secret_value())
        finally:
            hash_slots.release()
        user = auth_store.register(payload.email, payload.display_name, password_hash)
        return session_response(request, response, user)
    except ValueError as exc:
        raise HTTPException(409, 'Unable to create an account with those details.') from exc
    except (DatabaseUnavailable, SQLAlchemyError) as exc:
        raise HTTPException(503, 'Account storage is unavailable. Try again shortly.') from exc


@router.post('/login', dependencies=[Depends(require_json_client)])
def login(payload: Credentials, request: Request, response: Response):
    try:
        throttle(request, payload.email, 'login')
        user = auth_store.find_user(payload.email)
        stored_hash = user.get('password_hash') if user and user['is_active'] else None
        if not hash_slots.acquire(blocking=False):
            raise HTTPException(429, 'Sign-in service is busy. Try again shortly.')
        try:
            valid, updated_hash = hasher.verify_and_update(payload.password.get_secret_value(), stored_hash or dummy_hash)
        except password_errors.UnknownHashError:
            valid, updated_hash = False, None
        finally:
            hash_slots.release()
        if not valid or not stored_hash:
            raise HTTPException(401, 'Email or password is incorrect.')
        if updated_hash:
            auth_store.update_hash(user['user_id'], updated_hash)
        return session_response(request, response, user)
    except (DatabaseUnavailable, SQLAlchemyError) as exc:
        raise HTTPException(503, 'Account storage is unavailable. Try again shortly.') from exc


@router.get('/me')
def me(response: Response, user: Principal = Depends(require_user)):
    response.headers['Cache-Control'] = 'no-store'
    return {'user': {'user_id': user.user_id, 'email': user.email, 'display_name': user.display_name},
            'csrf_token': user.csrf_token, 'expires_at': user.expires_at}


@router.post('/logout', status_code=204)
def logout(request: Request, response: Response, user: Principal = Depends(require_user)):
    try:
        auth_store.revoke_session(request.cookies[COOKIE_NAME])
    except (DatabaseUnavailable, SQLAlchemyError) as exc:
        raise HTTPException(503, 'Could not end the session. Try again shortly.') from exc
    response.delete_cookie(COOKIE_NAME, path='/api', httponly=True, samesite='lax',
                           secure=os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true')
    response.headers['Cache-Control'] = 'no-store'
