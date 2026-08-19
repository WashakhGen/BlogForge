from pydantic import BaseModel, EmailStr, Field

"""Password Reset Schemas"""


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(max_length=120)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):     # Already Logged In users
    current_password: str
    new_password: str = Field(min_length=8)
