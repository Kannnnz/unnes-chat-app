import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Project Paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
FAISS_INDEX_PATH = VECTOR_STORE_DIR / "unnes_docs.faiss"

# JWT Settings
SECRET_KEY = os.getenv("APP_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Database Settings (PostgreSQL)
# Kita akan menggunakan satu URL koneksi yang disediakan oleh Neon atau dari .env lokal
DATABASE_URL = os.getenv("DATABASE_URL")

# RAG Service Settings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Google OAuth Settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Setup Script Settings
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "adminUnnesKuat123!")


# Validasi saat startup
if not SECRET_KEY or SECRET_KEY == "ganti_dengan_kunci_rahasia_yang_sangat_aman_dan_panjang":
    raise ValueError("APP_SECRET_KEY tidak diatur di file .env. Ini sangat tidak aman.")