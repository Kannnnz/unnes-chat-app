# file: app/core/config.py

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path('.').resolve() / '.env'
load_dotenv(dotenv_path=env_path)

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "a-very-secret-key-for-dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
API_V1_PREFIX = "/api/v1"

DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("FATAL: DATABASE_URL tidak diatur di environment.")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("FATAL: GOOGLE_API_KEY tidak diatur di environment.")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
FAISS_INDEX_PATH = VECTOR_STORE_DIR / "unnes_docs.faiss"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
