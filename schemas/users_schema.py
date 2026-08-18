
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# User
class UserBase(BaseModel):
    username: str = Field(min_length=2,max_length=50, description="The username of the user")
    email: EmailStr = Field(max_length=120, description="The email of the user")

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=200, description="The password of the user")


class UserPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    image_file: str | None = None
    image_path: str

class UserPrivateResponse(UserPublicResponse):
    email: EmailStr


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=2,max_length=50, description="The username of the user")
    email: EmailStr | None = Field(default=None, max_length=120, description="The email of the user")
    image_file: str | None = Field(default=None, min_length=2,max_length=200, description="Image file Name")

class Token(BaseModel):
    access_token: str
    token_type: str

