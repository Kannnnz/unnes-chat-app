# file: app/api/routers/documents.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from typing import List
import uuid
from pathlib import Path
from datetime import datetime
from psycopg2.extras import DictCursor
import traceback

from app.core import config
from app.db.session import get_db_connection
from app.api.deps import get_current_user
from app.schemas.user import UserInDB
from app.services.rag_service import rag_service
from app.schemas.document import DocumentInfo

router = APIRouter(prefix="/documents", tags=["Documents"])

def _background_rebuild_index():
    """Fungsi helper untuk menjalankan rebuild di background."""
    print("✅ Starting background task: Rebuild Index")
    try:
        rag_service.rebuild_index_from_db()
    except Exception:
        print("❌ BACKGROUND REBUILD FAILED:")
        traceback.print_exc()

@router.post("/upload")
async def upload_documents(
    files: List[UploadFile],
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_user)
):
    username = current_user.username
    user_dir = config.UPLOAD_DIR / username
    user_dir.mkdir(exist_ok=True)
    
    uploaded_docs_info = []

    for file in files:
        doc_id = str(uuid.uuid4())
        file_path = user_dir / f"{doc_id}{Path(file.filename).suffix}"
        
        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Dokumen ditandai sebagai terindeks (is_indexed=TRUE) secara optimis
                    query = "INSERT INTO documents (id, username, filename, file_path, upload_date, file_size, is_indexed) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    values = (doc_id, username, file.filename, str(file_path.resolve()), datetime.now(), len(content), True)
                    cursor.execute(query, values)
                    conn.commit()
            
            uploaded_docs_info.append({"id": doc_id, "filename": file.filename, "upload_date": datetime.now()})

        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Gagal menyimpan file {file.filename}: {e}")

    # Setelah SEMUA file berhasil diunggah dan disimpan di DB,
    # picu SATU background task untuk membangun ulang seluruh index.
    if uploaded_docs_info:
        background_tasks.add_task(_background_rebuild_index)

    return {"message": "File berhasil diterima. Proses indexing dimulai di latar belakang.", "uploaded_documents": uploaded_docs_info}

@router.get("/documents", response_model=list[DocumentInfo])
def get_documents(current_user: UserInDB = Depends(get_current_user)):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT id, filename, upload_date, is_indexed FROM documents WHERE username = %s ORDER BY upload_date DESC", (current_user.username,))
        docs = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in docs]
