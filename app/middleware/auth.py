"""
JWT Auth Middleware for FastAPI.
Validates JWT tokens from NextAuth.js frontend and API keys.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader

from sqlalchemy.orm import Session

from app.models.db import User
from app.models.database import get_db

# Config
JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ─────────────────────────────────────────────
# TOKEN CREATION
# ─────────────────────────────────────────────
def create_access_token(user_id: str, email: str, is_admin: bool = False) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "is_admin": is_admin,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ─────────────────────────────────────────────
# DEPENDENCY: Get Current User
# ─────────────────────────────────────────────
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts the current user from:
    1. Bearer JWT token (from NextAuth.js frontend)
    2. X-API-Key header (for REST API access)
    
    Raises 401 if neither is provided or valid.
    """
    user = None
    
    # Try Bearer token first
    if credentials and credentials.credentials:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
    
    # Fall back to API key
    if not user and api_key:
        user = db.query(User).filter(User.api_key == api_key).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token or X-API-Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency: require admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ─────────────────────────────────────────────
# PASSWORD HASHING (for email/password auth)
# ─────────────────────────────────────────────
from hashlib import sha256
import secrets

def hash_password(password: str) -> str:
    """Hash a password with a random salt."""
    salt = secrets.token_hex(16)
    hashed = sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against its stored hash."""
    salt, hashed = stored_hash.split(":", 1)
    return sha256(f"{salt}{password}".encode()).hexdigest() == hashed
