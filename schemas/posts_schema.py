
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.users_schema import UserPublicResponse


# Creating and repeating posts
class postBase(BaseModel):
    title: str = Field(min_length=5,max_length=100, description="The title of the post")
    content: str = Field(min_length=6, description="The content of the post")

class postCreate(postBase):
    pass

class postUpdate(BaseModel):
    title: str | None = Field(defualt=None, min_length=5,max_length=100, description="The title of the post")
    content: str | None = Field(default=None, min_length=6, description="The content of the post")


class postResponse(postBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    date_posted: datetime
    author: UserPublicResponse

class PaginatedPostResponse(BaseModel):
    posts: list[postResponse]   # posts
    total: int                  # Total count of posts in DB
    skip: int                   # Current Offset
    limit: int                  # How many post requests
    has_more: bool              # If there are more posts