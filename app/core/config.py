# app/core/config.py

import os
from pathlib import Path
from dotenv import load_dotenv

# Muat variabel dari file .env
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Konfigurasi Aplikasi
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")
if not APP_SECRET_KEY:
    # Di lingkungan produksi seperti Render, ini harus diatur sebagai Environment Variable
    # dan tidak akan menyebabkan error. Error ini untuk pengembangan lokal.
    print("PERINGATAN: APP_SECRET_KEY tidak diatur. Menggunakan nilai default yang tidak aman.")
    APP_SECRET_KEY = "your-default-secret-key-for-local-dev-only"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 hari

# Prefix API
API_V1_PREFIX = "/api/v1"

# Konfigurasi Database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL tidak diatur di file .env atau environment.")

# Konfigurasi Google
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY tidak diatur di file .env atau environment.")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Konfigurasi Direktori
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
