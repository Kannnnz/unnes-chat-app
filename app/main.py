# app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.core import config
from app.api.routers import auth, documents, chat, admin
from app.db.session import get_db_connection
from app.services.rag_service import rag_service

# Membuat direktori yang diperlukan jika belum ada
config.UPLOAD_DIR.mkdir(exist_ok=True)
config.VECTOR_STORE_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="UNNES Document Chat System",
    version="8.0.0"
)

# Middleware CORS untuk mengizinkan semua origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Menyertakan semua router API dengan prefix dari config
app.include_router(auth.router, prefix=config.API_V1_PREFIX)
app.include_router(documents.router, prefix=config.API_V1_PREFIX)
app.include_router(chat.router, prefix=config.API_V1_PREFIX)
app.include_router(admin.router, prefix=config.API_V1_PREFIX)

# Mounting direktori statis untuk frontend (HTML, CSS, JS)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_index():
    """Menyajikan file index.html sebagai halaman utama."""
    return FileResponse(STATIC_DIR / 'index.html')

@app.get("/health", tags=["System"])
def health_check():
    """Endpoint untuk memeriksa status kesehatan sistem."""
    db_status = "disconnected"
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    rag_status = "connected" if rag_service.is_ready else "disconnected"
    
    llm_status = "unknown"
    try:
        if rag_service.retrieval_chain.combine_docs_chain.llm:
            llm_status = "connected"
        else:
            llm_status = "disconnected"
    except Exception:
        llm_status = "disconnected"
    
    final_status = "healthy" if all(s == "connected" for s in [db_status, rag_status, llm_status]) else "degraded"

    return {
        "status": final_status,
        "database": db_status,
        "rag_service": rag_status,
        "llm_google_gemini": llm_status
    }
