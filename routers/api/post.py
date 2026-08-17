from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from databases import models
from databases.database import get_db
from schemas.posts_schema import postCreate, postResponse, postUpdate

router = APIRouter()


# Create a Post
@router.post(
    "",
    response_model=postResponse,
    status_code=status.HTTP_201_CREATED,
)

async def create_post(post: postCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.posts))
        .where(models.User.id == post.user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post



# Return All Posts
@router.get("", response_model=list[postResponse]) 
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    results = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = results.scalars().all()
    return posts
     

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
async def update_post_full(post_id: int, post_data: postCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    post = await get_post(post_id, db)

    if post_data.user_id != post.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this post",
        )
    
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

@router.patch("/{post_id}", response_model=postResponse)
async def update_post_partial(post_id: int, post_data: postUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    post = await get_post(post_id, db)

    update_data = post_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(post, key, value)
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    post = await get_post(post_id, db)
    await db.delete(post)
    await db.commit()

