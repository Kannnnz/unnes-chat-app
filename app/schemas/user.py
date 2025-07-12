# app/schemas/user.py

from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import List

# Model dasar untuk informasi pengguna yang bisa dibagikan secara publik
class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        from_attributes = True  # Untuk Pydantic v2

# Model untuk membuat pengguna baru
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator('email')
    def must_be_unnes_email(cls, v):
        if not (v.endswith('@students.unnes.ac.id') or v.endswith('@mail.unnes.ac.id')):
            raise ValueError('Hanya email UNNES yang diizinkan')
        return v

# Model untuk representasi pengguna di dalam database (termasuk hash password)
class UserInDB(UserPublic):
    password_hash: str | None = None

# Model untuk token JWT
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str | None = None

# Model untuk token dari Google Sign-In
class GoogleToken(BaseModel):
    token: str

# Model untuk statistik admin
class AdminStats(BaseModel):
    total_users: int
    total_documents: int
    total_chats: int
    admin_count: int
    user_count: int

# Model untuk daftar aktivitas
class ActivityLog(BaseModel):
    timestamp: datetime
    username: str
    activity: str
