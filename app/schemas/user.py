from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import List

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not (v.endswith('@students.unnes.ac.id') or v.endswith('@mail.unnes.ac.id')):
            raise ValueError('Email harus dari domain UNNES')
        return v

class UserInDB(UserBase):
    role: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class GoogleToken(BaseModel):
    credential: str

class AdminStats(BaseModel):
    total_users: int
    total_documents: int
    total_chats: int
