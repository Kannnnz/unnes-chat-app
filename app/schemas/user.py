# file: app/schemas/user.py

from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime

class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator('email')
    def must_be_unnes_email(cls, v):
        if not (v.endswith('@students.unnes.ac.id') or v.endswith('@mail.unnes.ac.id')):
            raise ValueError('Hanya email UNNES yang diizinkan')
        return v

class UserInDB(UserPublic):
    password_hash: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class GoogleToken(BaseModel):
    token: str

class AdminStats(BaseModel):
    total_users: int
    total_documents: int
    total_chats: int
