# app/api/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from psycopg2.extras import DictCursor

# Import untuk Google Auth
from google.oauth2 import id_token
from google.auth.transport import requests

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
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Gagal mendaftarkan pengguna: {e}")
        finally:
            cursor.close()
    
    return new_user

@router.post("/token", response_model=Token)
def login_with_password(form_data: OAuth2PasswordRequestForm = Depends()):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s", (form_data.username,))
        user = cursor.fetchone()
        cursor.close()
    
    if not user or not security.verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@router.post("/google", response_model=Token)
def login_with_google(token_data: GoogleToken):
    if not config.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Login is not configured on the server."
        )
    try:
        id_info = id_token.verify_oauth2_token(
            token_data.token, requests.Request(), config.GOOGLE_CLIENT_ID
        )
        email = id_info['email']

        if not (email.endswith('@students.unnes.ac.id') or email.endswith('@mail.unnes.ac.id')):
            raise HTTPException(status_code=403, detail="Hanya akun email UNNES yang diizinkan.")

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Google token"
        )

    username = email.split('@')[0]
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            # Pengguna baru dari Google
            role = 'admin' if email.endswith('@mail.unnes.ac.id') else 'user'
            # Buat hash password acak karena pengguna ini hanya akan login via Google
            dummy_password = security.get_password_hash(f"google_sso_{datetime.now().timestamp()}")
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role, is_google_user) VALUES (%s, %s, %s, %s, %s) RETURNING *",
                (username, email, dummy_password, role, True)
            )
            user = cursor.fetchone()
            conn.commit()
        
        cursor.close()
    
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@router.get("/profile", response_model=UserPublic, tags=["User"])
def read_current_user(current_user: UserInDB = Depends(get_current_user)):
    return current_user
