# file: app/db/session.py

import psycopg2
from contextlib import contextmanager
from fastapi import HTTPException
from app.core import config

DATABASE_URL = config.DATABASE_URL

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    except psycopg2.OperationalError as e:
        raise HTTPException(status_code=503, detail=f"Database connection error: {e}")
    finally:
        if conn:
            conn.close()
