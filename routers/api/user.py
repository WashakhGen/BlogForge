from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from authetication.auth import (
    create_access_token,
    hash_password,
    oauth2_scheme,
    verify_access_token,
    verify_password,
)
from core.settings import settings
from databases import models
from databases.database import get_db
from schemas.posts_schema import postResponse
from schemas.users_schema import (
    Token,
    UserCreate,
    UserPrivateResponse,
    UserPublicResponse,
    UserUpdate,
)

router = APIRouter()
""

@router.post(
    "",
    response_model=UserPrivateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_create(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(
            or_(func.lower(models.User.username) == user.username.lower(), func.lower(models.User.email) == user.email.lower())
        )
    )
    existing_user = result.scalars().first()

    if existing_user:
        detail = "Username already exists" if existing_user.username == user.username else "Email already exists"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
    
    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


## Login ##

@router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(get_db)]
    ):

    ## Look up user by email (CASE insensitive)
    # Note: OAuth2PasswordRequestForm uses "username" field, but  treat it as email
    result = await db.execute(
        select(models.User).where(models.User.email == form_data.username.lower())
    )
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token = access_token, token_type ="bearer")



@router.get("/me", response_model=UserPrivateResponse)
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           db: Annotated[AsyncSession, Depends(get_db)]
                        ):

    """Get the currently authenticated user."""
    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate user_id is a valid integer (defense agaiinst malformed jwt)
    try:
        user_id_int = int(user_id)
    except (TypeError,ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(models.User).where(models.User.id == user_id_int)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user



@router.get("/{user_id}", response_model=UserPublicResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
            select(models.User).
            where(models.User.id == user_id)
        )
    user = result.scalars().first()
    if user:
        return user

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get("/{user_id}/posts", response_model=list[postResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    await get_user(user_id, db)

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
    )
    posts = result.scalars().all()
    return posts


@router.patch("/{user_id}", response_model=UserPrivateResponse)
async def update_user_partial(user_id: int, user_data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await get_user(user_id, db)

    conditions = []
    if user_data.username is not None and user_data.username.lower() != user.username.lower():
        conditions.append(func.lower(models.User.username) == user_data.username.lower())
    if user_data.email is not None and user_data.email.lower() != user.email.lower():
        conditions.append(func.lower(models.User.email) == user_data.email.lower())

    if conditions:
        result = await db.execute(select(models.User).where(or_(*conditions)))
        existing_user = result.scalars().first()
        if existing_user:
            detail = (
                "Username already exists"
                if existing_user.username == user_data.username
                else "Email already exists"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

    update_data = user_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await get_user(user_id, db)
    await db.delete(user)
    await db.commit()
