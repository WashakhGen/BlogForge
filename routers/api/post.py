from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from authetication.auth import CurrentUser
from databases import models
from databases.database import get_db
from schemas.posts_schema import (
    PaginatedPostResponse,
    postCreate,
    postResponse,
    postUpdate,
)

router = APIRouter()


# Create a Post
@router.post(
    "",
    response_model=postResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(post: postCreate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):

    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=current_user.id,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post



# Return All Posts
@router.get("", response_model=PaginatedPostResponse) 
async def get_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    ):

    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0


    results = await db.execute(select(models.Post)
                    .options(selectinload(models.Post.author))
                    .order_by(models.Post.date_posted.desc())
                    .offset(skip)
                    .limit(limit),
                )
    posts = results.scalars().all()

    has_more = skip + len(posts) < total

    return PaginatedPostResponse(
        posts= [postResponse.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more
    )
     

# Return Single Post 
@router.get("/{post_id}", response_model=postResponse)
async def get_post(post_id: int , db: Annotated[AsyncSession, Depends(get_db)]):

    results = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = results.scalars().first()
    if post:
        return post
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found" 
    )


@router.put("/{post_id}", response_model=postResponse)
async def update_post_full(post_id: int, post_data: postCreate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    post = await get_post(post_id, db)

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            details = "Not authorized to update this post"
        )

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

@router.patch("/{post_id}", response_model=postResponse)
async def update_post_partial(post_id: int, post_data: postUpdate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    post = await get_post(post_id, db)

    if post.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail = "Not authorized to update this post"
            )
    

    update_data = post_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(post, key, value)
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    post = await get_post(post_id, db)

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            details = "Not authorized to delete this post"
        )


    await db.delete(post)
    await db.commit()

