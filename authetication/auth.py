from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.settings import settings
from databases import models
from databases.database import get_db

password_hash = PasswordHash.recommended()      # secure defaults
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return password_hash.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> str | None:
    """Verify a JWT access token and return the subject (user id) if valid, otherwise return None."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub"]}  # Ensure 'exp' and 'sub' claims are present
        )
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None

async def get_current_user(
        tokken: Annotated[str, Depends(oauth2_scheme)],
        db: Annotated[AsyncSession, Depends(get_db)],
) -> models.User :
    user_id = verify_access_token(tokken)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token",
            headers={"WWW-Authenticate": "Bearer"},
        ) 

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Token",
                headers={"WWW-Authenticate": "Bearer"},
                ) 

    result = await db.execute(
        select(models.User).where(models.User.id == user_id_int)
    )

    user = result.scalars().first()
    if not user:
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Token",
                headers={"WWW-Authenticate": "Bearer"},
                ) 
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]