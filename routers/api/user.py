from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from PIL import UnidentifiedImageError
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from authentication.auth import (
    CurrentUser,
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from core.settings import settings
from databases import models
from databases.database import get_db
from schemas.password_reset import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from schemas.posts_schema import PaginatedPostResponse, postResponse
from schemas.users_schema import (
    Token,
    UserCreate,
    UserPrivateResponse,
    UserPublicResponse,
    UserUpdate,
)
from utils.email_utils import send_password_reset_email
from utils.image_utils import delete_profile_image, process_profile_image

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
            or_(
                func.lower(models.User.username) == user.username.lower(),
                func.lower(models.User.email) == user.email.lower(),
            )
        )
    )
    existing_user = result.scalars().first()

    if existing_user:
        detail = (
            "Username already exists"
            if existing_user.username == user.username
            else "Email already exists"
        )
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
    db: Annotated[AsyncSession, Depends(get_db)],
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
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivateResponse)
async def get_current_user(current_user: CurrentUser):
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forget_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == request_data.email.lower()
        )
    )

    user = result.scalars().first()

    if user:
        await db.execute(
            sql_delete(models.PasswordResetToken).where(
                models.PasswordResetToken.user_id == user.id
            )
        )

        token = generate_reset_token()
        token_hash = hash_reset_token(token=token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.RESET_TOKEN_EXPIRE_MIN
        )

        reset_token = models.PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token,
        )

    return {
        "message": "If an account exists with this email, You will receive password reset instructions."
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    token_hash = hash_reset_token(request_data.token)
    result = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token_hash == token_hash,
        ),
    )

    reset_token = result.scalars().first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or Expired reset token",
        )

    if reset_token.expires_at < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or Expired reset token",
        )

    result = await db.execute(
        select(models.User).where(models.User.id == reset_token.user_id),
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or Expired reset token",
        )

    user.password_hash = hash_password(request_data.new_password)

    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == user.id
        )
    )

    await db.commit()
    return {
        "message": "Password reset successfully, You can now log in with your new Password."
    }


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current Password is not correct",
        )

    current_user.password_hash = hash_password(password_data.new_password)

    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == current_user.id
        )
    )

    await db.commit()
    return {"message": "Password Changed Successfully"}


@router.get("/{user_id}", response_model=UserPublicResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user:
        return user

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get("/{user_id}/posts", response_model=PaginatedPostResponse)
async def get_user_posts(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.POST_PER_PAGE,
):
    await get_user(user_id, db)

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
        .offset(skip)
        .limit(limit),
    )

    posts = result.scalars().all()
    has_more = skip + len(posts) < total

    return PaginatedPostResponse(
        posts=[postResponse.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.patch("/{user_id}", response_model=UserPrivateResponse)
async def update_user_partial(
    user_id: int,
    user_data: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to Update this User",
        )

    user = await get_user(user_id, db)
    conditions = []
    if (
        user_data.username is not None
        and user_data.username.lower() != user.username.lower()
    ):
        conditions.append(
            func.lower(models.User.username) == user_data.username.lower()
        )
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
async def delete_user(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to Delete this User",
        )
    user = await get_user(user_id, db)

    old_filename = user.image_file

    await db.delete(user)
    await db.commit()

    if old_filename:
        delete_profile_image(old_filename)


@router.patch("/{user_id}/picture", response_model=UserPrivateResponse)
async def upload_profile_picture(
    user_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Authorized to update this Users Picture",
        )

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum Size is {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MBs",
        )

    try:
        new_filename = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file."
        ) from err

    old_filename = current_user.image_file
    current_user.image_file = new_filename
    await db.commit()
    await db.refresh(current_user)

    if old_filename:
        delete_profile_image(old_filename)

    return current_user


@router.delete("/{user_id}/picture", response_model=UserPrivateResponse)
async def delete_profile_picture(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Authorized to update this Users Picture",
        )

    old_filename = current_user.image_file

    if old_filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to Delete",
        )

    current_user.image_file = None
    await db.commit()
    await db.refresh(current_user)

    delete_profile_image(old_filename)
    return current_user
