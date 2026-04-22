"""
Authentication utilities — JWT tokens + password hashing.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config import JWT_SECRET_KEY as SECRET_KEY
from backend.db import get_db
from backend.models import User

# ── Config ───────────────────────────────────────────────────────-

_DEFAULT_KEY = "career-planning-agent-dev-secret-change-in-prod"
if SECRET_KEY == _DEFAULT_KEY:
    import sys
    # Dev mode: auto-generate a random key per-process (sessions reset on restart, acceptable for dev)
    if os.getenv("ENV", "development").lower() in ("production", "prod"):
        raise RuntimeError(
            "FATAL: JWT_SECRET_KEY is not set. "
            "Set it in .env before starting the production server."
        )
    SECRET_KEY = secrets.token_hex(32)
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY not set — using a randomly generated key (sessions reset on restart). "
        "Set JWT_SECRET_KEY in .env for stable sessions.",
        stacklevel=2,
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72

# ── Password hashing (PBKDF2-SHA256, stdlib only) ────────────────


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"pbkdf2:sha256:260000${salt}${dk.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        parts = hashed.split("$")
        salt = parts[1]
        stored_dk = parts[2]
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 260_000)
        return hmac.compare_digest(dk.hex(), stored_dk)
    except (IndexError, ValueError):
        return False


# ── JWT ───────────────────────────────────────────────────────────

def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── FastAPI dependency ────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from the JWT bearer token. Raises 401 on failure."""
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


