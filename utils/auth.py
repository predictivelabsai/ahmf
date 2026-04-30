"""
User authentication and credential management.

Provides password hashing (bcrypt), user CRUD, and JWT token handling.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

import bcrypt as _bcrypt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return _bcrypt.checkpw(password.encode(), password_hash.encode())


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

def _get_pool():
    from utils.db import get_pool
    return get_pool()


def create_user(
    email: str,
    password: str,
    display_name: Optional[str] = None,
    role: str = "user",
) -> Optional[Dict]:
    """Create a new user. Returns user dict or None if email already exists."""
    from sqlalchemy import text

    pw_hash = hash_password(password)
    pool = _get_pool()
    with pool.get_session() as session:
        result = session.execute(
            text("""
                INSERT INTO ahmf.users
                    (email, password_hash, display_name, role)
                VALUES
                    (:email, :pw_hash, :display_name, :role)
                ON CONFLICT (email) DO NOTHING
                RETURNING user_id, email, display_name, role, created_at
            """),
            {
                "email": email.lower().strip(),
                "pw_hash": pw_hash,
                "display_name": display_name or email.split("@")[0],
                "role": role,
            },
        )
        row = result.fetchone()
        if not row:
            return None
        return _row_to_user(row, result.keys())


def get_user_by_email(email: str) -> Optional[Dict]:
    """Fetch a user by email address."""
    from sqlalchemy import text
    pool = _get_pool()
    with pool.get_session() as session:
        result = session.execute(
            text("""
                SELECT user_id, email, password_hash, display_name, role, created_at
                FROM ahmf.users
                WHERE email = :email
            """),
            {"email": email.lower().strip()},
        )
        row = result.fetchone()
        if not row:
            return None
        return _row_to_user(row, result.keys())


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Fetch a user by user_id (UUID)."""
    from sqlalchemy import text
    pool = _get_pool()
    with pool.get_session() as session:
        result = session.execute(
            text("""
                SELECT user_id, email, password_hash, display_name, role, created_at
                FROM ahmf.users
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        )
        row = result.fetchone()
        if not row:
            return None
        return _row_to_user(row, result.keys())


def authenticate(email: str, password: str) -> Optional[Dict]:
    """Authenticate by email + password. Returns user dict on success, None on failure."""
    user = get_user_by_email(email)
    if not user:
        return None
    pw_hash = user.get("password_hash")
    if not pw_hash:
        return None
    if not verify_password(password, pw_hash):
        return None
    user.pop("password_hash", None)
    return user


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_jwt_token(user_id: str, email: str) -> str:
    """Create a JWT token for session authentication."""
    import jwt

    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET not set in .env")
    payload = {
        "user_id": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_jwt_token(token: str) -> Optional[Dict]:
    """Decode and verify a JWT token. Returns payload dict or None."""
    import jwt

    secret = os.getenv("JWT_SECRET")
    if not secret:
        return None
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.debug("JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid JWT: {e}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_password_reset_token(user_id: str) -> str:
    """Create a password reset token (expires in 1 hour)."""
    import jwt
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET not set in .env")
    payload = {
        "user_id": str(user_id),
        "purpose": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def reset_password_with_token(token: str, new_password: str) -> bool:
    """Verify a reset token and update the user's password. Returns True on success."""
    import jwt
    secret = os.getenv("JWT_SECRET")
    if not secret:
        return False
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False
    if payload.get("purpose") != "password_reset":
        return False
    user_id = payload.get("user_id")
    if not user_id:
        return False
    pw_hash = hash_password(new_password)
    from sqlalchemy import text
    pool = _get_pool()
    with pool.get_session() as session:
        result = session.execute(
            text("UPDATE ahmf.users SET password_hash = :pw_hash, updated_at = NOW() WHERE user_id = :user_id"),
            {"pw_hash": pw_hash, "user_id": user_id},
        )
        return result.rowcount > 0


def _row_to_user(row, keys) -> Dict:
    """Convert a DB row to a user dict."""
    d = dict(zip(keys, row))
    if d.get("user_id"):
        d["user_id"] = str(d["user_id"])
    return d
