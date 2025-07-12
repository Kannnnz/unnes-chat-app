# app/core/config.py

import os
from pathlib import Path
from dotenv import load_dotenv

# Muat variabel dari file .env untuk pengembangan lokal
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# --- Konfigurasi Aplikasi ---
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")
if not APP_SECRET_KEY:
    print("PERINGATAN: APP_SECRET_KEY tidak diatur. Menggunakan nilai default yang tidak aman.")
    APP_SECRET_KEY = "your-default-secret-key-for-local-dev-only"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 hari
API_V1_PREFIX = "/api/v1"

# --- Konfigurasi Admin Default ---
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")
if not DEFAULT_ADMIN_PASSWORD:
    print("PERINGATAN: DEFAULT_ADMIN_PASSWORD tidak diatur. Menggunakan 'admin123' sebagai default.")
    DEFAULT_ADMIN_PASSWORD = "admin123"

# --- Konfigurasi Database ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL tidak diatur di file .env atau environment.")

# --- Konfigurasi Google ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY tidak diatur di file .env atau environment.")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# --- Konfigurasi Direktori ---
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
