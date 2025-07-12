from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from typing import Dict

from app.core import config
from app.db.session import get_db_connection

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, email, role FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
    
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user