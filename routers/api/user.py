from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from databases import models
from databases.database import get_db
from schemas.posts_schema import postResponse
from schemas.users_schema import UserCreate, UserResponse, UserUpdate

router = APIRouter()
""

@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_create(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(
            or_(models.User.username == user.username, models.User.email == user.email)
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
        email=user.email,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("/{user_id}", response_model=UserResponse)
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


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_partial(user_id: int, user_data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await get_user(user_id, db)

    conditions = []
    if user_data.username is not None and user_data.username != user.username:
        conditions.append(models.User.username == user_data.username)
    if user_data.email is not None and user_data.email != user.email:
        conditions.append(models.User.email == user_data.email)

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
