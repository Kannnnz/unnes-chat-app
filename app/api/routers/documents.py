# file: app/api/routers/documents.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from typing import List
import uuid
from pathlib import Path
from datetime import datetime
from psycopg2.extras import DictCursor

from app.core import config
from app.db.session import get_db_connection
from app.api.deps import get_current_user
from app.schemas.user import UserInDB
from app.services.rag_service import rag_service, load_and_split_document
from app.schemas.document import DocumentInfo

router = APIRouter(prefix="/documents", tags=["Documents"])

def _process_and_index_file(doc_id: str, file_path: Path, filename: str, owner: str):
    """
    Fungsi ini berjalan di background untuk memproses dan mengindeks file.
    """
    print(f"Starting background processing for: {filename}")
    try:
        chunks = load_and_split_document(file_path)
        if chunks:
            for chunk in chunks:
                chunk.metadata.update({"doc_id": doc_id, "filename": filename, "owner": owner})
            
            rag_service.add_documents_to_index(chunks)
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE documents SET is_indexed = TRUE WHERE id = %s", (doc_id,))
                    conn.commit()
            print(f"Successfully processed and indexed: {filename}")
        else:
            print(f"No content to process for: {filename}")
    except Exception as e:
        print(f"❌ BACKGROUND TASK FAILED for {filename}: {e}")

@router.post("/upload")
async def upload_documents(
    files: List[UploadFile],
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_user)
):
    if not rag_service.is_ready:
        raise HTTPException(status_code=503, detail="Sistem RAG tidak siap.")
    
    username = current_user.username
    user_dir = config.UPLOAD_DIR / username
    user_dir.mkdir(exist_ok=True)
    
    uploaded_docs_info = []

    for file in files:
        doc_id = str(uuid.uuid4())
        file_path = user_dir / f"{doc_id}{Path(file.filename).suffix}"
        
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    query = "INSERT INTO documents (id, username, filename, file_path, upload_date, file_size, is_indexed) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    values = (doc_id, username, file.filename, str(file_path.resolve()), datetime.now(), len(content), False)
                    cursor.execute(query, values)
                    conn.commit()

            background_tasks.add_task(_process_and_index_file, doc_id, file_path, file.filename, username)
            
            uploaded_docs_info.append({"id": doc_id, "filename": file.filename, "upload_date": datetime.now()})

        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Gagal menyimpan file {file.filename}: {e}")

    # PERBAIKAN DI SINI: Mengubah 'uploaded_files' menjadi 'uploaded_documents'
    return {"message": "File diterima dan sedang diproses.", "uploaded_documents": uploaded_docs_info}

@router.get("/documents", response_model=list[DocumentInfo])
def get_documents(current_user: UserInDB = Depends(get_current_user)):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT id, filename, upload_date FROM documents WHERE username = %s ORDER BY upload_date DESC", (current_user.username,))
        docs = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in docs]
