from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.settings import settings
from databases import models
from databases.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

SIDEBAR_POST_COUNT = 5


async def get_sidebar_posts(db: AsyncSession) -> list[models.Post]:
    """Most recent posts, used to populate the "Latest Posts" sidebar widget on every page."""
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .limit(SIDEBAR_POST_COUNT),
    )
    return list(result.scalars().all())


@router.get("/", include_in_schema=False, name="home")  # Home decorater
@router.get("/posts", include_in_schema=False, name="posts")  # Post Route
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):

    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar()

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .limit(settings.POST_PER_PAGE),
    )
    posts = result.scalars().all()

    has_more = len(posts) < total

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": posts,
            "title": "Home",
            "limit": settings.POST_PER_PAGE,
            "has_more": has_more,
            "sidebar_posts": await get_sidebar_posts(db),
        },
    )


# Return Single Post Page Route
@router.get("/posts/{post_id}", include_in_schema=False)  # Post Route
async def post_page(
    post_id: int, request: Request, db: Annotated[AsyncSession, Depends(get_db)]
):
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
            {
                "post": post,
                "title": post.title,
                "sidebar_posts": await get_sidebar_posts(db),
            },
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@router.get("/users/{user_id}/posts", include_in_schema=False)
async def user_posts_page(
    user_id: int, request: Request, db: Annotated[AsyncSession, Depends(get_db)]
):

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    count_result = await db.execute(
        select(func.count())
        .select_from(models.Post)
        .where(models.Post.user_id == user_id),
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
        .limit(settings.POST_PER_PAGE),
    )

    posts = result.scalars().all()
    has_more = len(posts) < total
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": posts,
            "user": user,
            "title": f"{user.username}'s Posts",
            "limit": settings.POST_PER_PAGE,
            "has_more": has_more,
            "sidebar_posts": await get_sidebar_posts(db),
        },
    )


## login and register routes
@router.get("/login", include_in_schema=False)
async def login_page(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"title": "Login", "sidebar_posts": await get_sidebar_posts(db)},
    )


@router.get("/register", include_in_schema=False)
async def register_page(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
):
    return templates.TemplateResponse(
        request,
        "register.html",
        {"title": "Register", "sidebar_posts": await get_sidebar_posts(db)},
    )


@router.get("/account", include_in_schema=False)
async def account_page(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
):
    return templates.TemplateResponse(
        request,
        "account.html",
        {"title": "Account", "sidebar_posts": await get_sidebar_posts(db)},
    )


@router.get("/forgot-password", include_in_schema=False)
async def forgot_password_page(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
):
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"title": "Forgot Password", "sidebar_posts": await get_sidebar_posts(db)},
    )


@router.get("/reset-password", include_in_schema=False)
async def reset_password_page(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
):
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        {"title": "Reset Password", "sidebar_posts": await get_sidebar_posts(db)},
    )

    response.headers["Referrer-Policy"] = "no-referrer"
    return response



@router.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database Unavailable"
        ) from exc

    return {"status": "healthy"}