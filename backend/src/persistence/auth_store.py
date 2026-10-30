"""Database-backed accounts, hashed sessions and shared login throttles."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .database import session_scope


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def digest(value: str) -> str:
    return sha256(value.encode('utf-8')).hexdigest()


def csrf_token(token: str) -> str:
    return digest('csrf:' + token)


def register(email: str, display_name: str, password_hash: str) -> dict:
    user_id = str(uuid4())
    try:
        with session_scope() as session:
            session.execute(text('INSERT INTO app_users(user_id,email,display_name,password_hash,is_active) VALUES (:id,:email,:name,:hash,TRUE)'),
                            {'id': user_id, 'email': email, 'name': display_name, 'hash': password_hash})
    except IntegrityError as exc:
        raise ValueError('Unable to create an account with those details.') from exc
    return {'user_id': user_id, 'email': email, 'display_name': display_name}


def find_user(email: str):
    with session_scope() as session:
        row = session.execute(text('SELECT user_id,email,display_name,password_hash,is_active FROM app_users WHERE email=:email'), {'email': email}).mappings().first()
        return dict(row) if row else None


def update_hash(user_id: str, password_hash: str):
    with session_scope() as session:
        session.execute(text('UPDATE app_users SET password_hash=:hash WHERE user_id=:id'), {'hash': password_hash, 'id': user_id})


def create_session(user_id: str, hours: int, previous_token: str | None = None):
    token = secrets.token_urlsafe(32)
    expiry = now() + timedelta(hours=hours)
    with session_scope() as session:
        if previous_token:
            session.execute(text('DELETE FROM auth_sessions WHERE token_hash=:hash'), {'hash': digest(previous_token)})
        session.execute(text('DELETE FROM auth_sessions WHERE user_id=:id AND expires_at<=:now'), {'id': user_id, 'now': now()})
        session.execute(text('INSERT INTO auth_sessions(token_hash,user_id,expires_at) VALUES (:hash,:id,:expiry)'),
                        {'hash': digest(token), 'id': user_id, 'expiry': expiry})
    return token, expiry.replace(tzinfo=timezone.utc)


def read_session(token: str):
    with session_scope() as session:
        row = session.execute(text('''
            SELECT u.user_id,u.email,u.display_name,s.expires_at
            FROM auth_sessions s JOIN app_users u ON u.user_id=s.user_id
            WHERE s.token_hash=:hash AND s.expires_at>:now AND u.is_active=TRUE
        '''), {'hash': digest(token), 'now': now()}).mappings().first()
        if not row:
            return None
        return {**dict(row), 'expires_at': row['expires_at'].replace(tzinfo=timezone.utc)}


def revoke_session(token: str):
    with session_scope() as session:
        session.execute(text('DELETE FROM auth_sessions WHERE token_hash=:hash'), {'hash': digest(token)})


def throttle(key: str, limit: int, seconds: int) -> bool:
    """Atomically consume a fixed-window attempt across all API workers."""
    instant = now()
    cutoff = instant - timedelta(seconds=seconds)
    key_hash = digest(key)
    with session_scope() as session:
        session.execute(text('''
            INSERT INTO auth_rate_limits(bucket_key,attempts,window_started)
            VALUES (:key,1,:now)
            ON DUPLICATE KEY UPDATE
                attempts=IF(window_started<=:cutoff,1,attempts+1),
                window_started=IF(window_started<=:cutoff,:now,window_started)
        '''), {'key': key_hash, 'now': instant, 'cutoff': cutoff})
        attempts = session.execute(text('SELECT attempts FROM auth_rate_limits WHERE bucket_key=:key'), {'key': key_hash}).scalar_one()
    return attempts <= limit
