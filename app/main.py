# app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.core import config
from app.api.routers import auth, documents, chat, admin

config.UPLOAD_DIR.mkdir(exist_ok=True)
config.VECTOR_STORE_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="UNNES Document Chat System (Structured Version)",
    version="7.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=f"{API_V1_PREFIX}/auth")
app.include_router(documents.router, prefix=f"{API_V1_PREFIX}/documents")
app.include_router(chat.router, prefix=f"{API_V1_PREFIX}/chat")
app.include_router(admin.router, prefix=f"{API_V1_PREFIX}/admin")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_index():
    return FileResponse(STATIC_DIR / 'index.html')

@app.get("/health", tags=["System"])
def health_check():
    from app.db.session import get_db_connection
    from app.services.rag_service import rag_service
    
    db_status = "disconnected"
    try:
        with get_db_connection() as conn:
            # Coba jalankan query sederhana untuk memastikan koneksi hidup
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    rag_status = "connected" if rag_service.is_ready else "disconnected"
    
    # Periksa apakah RAG service punya LLM (model bahasa)
    llm_status = "unknown"
    if hasattr(rag_service, 'retrieval_chain') and rag_service.retrieval_chain:
        if hasattr(rag_service.retrieval_chain.combine_docs_chain, 'llm'):
            llm_status = "connected"
        else:
            llm_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" and rag_status == "connected" and llm_status == "connected" else "degraded",
        "database": db_status,
        "llm_ollama": llm_status
    }
