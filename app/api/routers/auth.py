# file: app/api/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from psycopg2.extras import DictCursor
from google.oauth2 import id_token
from google.auth.transport import requests
from datetime import datetime

from app.core import security, config
from app.db.session import get_db_connection
from app.schemas.user import UserCreate, Token, GoogleToken, UserPublic
from app.api.deps import get_current_user, UserInDB

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate):
    hashed_password = security.get_password_hash(user.password)
    role = 'admin' if user.email.endswith('@mail.unnes.ac.id') else 'user'
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING id, username, email, role, created_at",
                (user.username, user.email, hashed_password, role)
            )
            new_user = cursor.fetchone()
            conn.commit()
            cursor.close()
            return new_user
        except Exception:
            conn.rollback()
            raise HTTPException(status_code=400, detail="Username atau email mungkin sudah ada.")

@router.post("/token", response_model=Token)
def login_with_password(form_data: OAuth2PasswordRequestForm = Depends()):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s", (form_data.username,))
        user = cursor.fetchone()
        cursor.close()
    if not user or not user["password_hash"] or not security.verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = security.create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@router.post("/google", response_model=Token)
def login_with_google(token_data: GoogleToken):
    if not config.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google Login not configured.")
    try:
        id_info = id_token.verify_oauth2_token(token_data.token, requests.Request(), config.GOOGLE_CLIENT_ID)
        email = id_info['email']
        if not (email.endswith('@students.unnes.ac.id') or email.endswith('@mail.unnes.ac.id')):
            raise HTTPException(status_code=403, detail="Hanya email UNNES yang diizinkan.")
    except ValueError:
        raise HTTPException(status_code=401, detail="Could not validate Google token")

    username = email.split('@')[0]
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            role = 'admin' if email.endswith('@mail.unnes.ac.id') else 'user'
            cursor.execute("INSERT INTO users (username, email, role, is_google_user) VALUES (%s, %s, %s, %s) RETURNING *",
                           (username, email, role, True))
            user = cursor.fetchone()
            conn.commit()
        cursor.close()
    access_token = security.create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@router.get("/profile", response_model=UserPublic)
def read_current_user(current_user: UserInDB = Depends(get_current_user)):
    return current_user
