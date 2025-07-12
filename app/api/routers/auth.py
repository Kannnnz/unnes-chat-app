from psycopg2.extras import DictCursor
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import bcrypt
import jwt
from datetime import datetime, timedelta

# Import untuk Google Auth
from google.oauth2 import id_token
from google.auth.transport import requests

from app.core import config
from app.db.session import get_db_connection
from app.schemas.user import UserCreate, Token, GoogleToken
from app.api.deps import get_current_user

router = APIRouter()

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)

@router.post("/token", response_model=Token, tags=["Authentication"])
def login_with_password(form_data: OAuth2PasswordRequestForm = Depends()):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT username, password, role FROM users WHERE username = %s", (form_data.username,))
        user_db = cursor.fetchone()
        cursor.close()

    if not user_db or not verify_password(form_data.password, user_db["password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    expires_delta = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode = {"sub": user_db["username"], "exp": expire}
    access_token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    
    return {"access_token": access_token, "token_type": "bearer", "role": user_db["role"]}

@router.post("/google", response_model=Token, tags=["Authentication"])
def login_with_google(token_data: GoogleToken):
    if not config.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google Client ID not configured on server.")
    try:
        idinfo = id_token.verify_oauth2_token(
            token_data.credential, requests.Request(), config.GOOGLE_CLIENT_ID
        )
        email = idinfo['email']
        username = email.split('@')[0]
        
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate Google credentials")
    
    if not (email.endswith('@students.unnes.ac.id') or email.endswith('@mail.unnes.ac.id')):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya akun Google UNNES yang diizinkan.")

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT username, role FROM users WHERE email = %s", (email,))
        user_db = cursor.fetchone()

        if not user_db:
            print(f"User baru dari Google: {email}")
            role = 'admin' if email.endswith('@mail.unnes.ac.id') else 'user'
            new_password_hash = hash_password(f"google_sso_{datetime.now().timestamp()}")
            
            insert_query = "INSERT INTO users (username, email, password, role, created_at) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(insert_query, (username, email, new_password_hash, role, datetime.now()))
            conn.commit()
            user_role = role
        else:
            print(f"User lama dari Google: {email}")
            username = user_db['username']
            user_role = user_db['role']
        
        cursor.close()

    expires_delta = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode = {"sub": username, "exp": expire}
    access_token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)

    return {"access_token": access_token, "token_type": "bearer", "role": user_role}

@router.post("/register", status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register(user: UserCreate):
    hashed_pass = hash_password(user.password)
    role = 'admin' if user.email.endswith('@mail.unnes.ac.id') else 'user'
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            query = "INSERT INTO users (username, email, password, role, created_at) VALUES (%s, %s, %s, %s, %s)"
            values = (user.username, user.email, hashed_pass, role, datetime.now())
            cursor.execute(query, values)
            conn.commit()
        except Exception:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")
        finally:
            cursor.close()
            
    return {"message": "User registered successfully"}

@router.get("/profile", tags=["User"])
def get_user_profile(current_user: dict = Depends(get_current_user)):
    return current_user
