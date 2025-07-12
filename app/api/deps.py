# app/api/deps.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from psycopg2.extras import DictCursor

from app.core import config
from app.db.session import get_db_connection
from app.schemas.user import UserInDB

# Skema OAuth2 mengarah ke endpoint token yang benar menggunakan prefix dari config
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{config.API_V1_PREFIX}/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.APP_SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except (JWTError, ValidationError):
        raise credentials_exception

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        cursor.close()

    if user_data is None:
        raise credentials_exception

    return UserInDB(**user_data)

def require_admin(current_user: UserInDB = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
