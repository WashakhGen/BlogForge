from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from databases import models
from databases.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")




@router.get("/" , include_in_schema=False, name="home") # Home decorater
@router.get("/posts", include_in_schema=False, name="posts") # Post Route
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
   result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
   posts = result.scalars().all()
   return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"}
    )

# Return Single Post Page Route
@router.get("/posts/{post_id}", include_in_schema=False) # Post Route
async def post_page(post_id: int, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )
    post = result.scalars().first()
    if post:
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": post.title}
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@router.get("/users/{user_id}/posts", include_in_schema=False)
async def user_posts_page(user_id: int, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(
        select(models.User)
        .where(models.User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user":user, "title": f"{user.username}'s Posts"},
    )
