# file: app/api/routers/documents.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
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

@router.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...), current_user: UserInDB = Depends(get_current_user)):
    if not rag_service.is_ready:
        raise HTTPException(status_code=503, detail="Sistem RAG tidak siap.")
    
    username = current_user.username
    user_dir = config.UPLOAD_DIR / username
    user_dir.mkdir(exist_ok=True)
    uploaded_docs_info = []

    for file in files:
        doc_id = str(uuid.uuid4())
        # Pastikan path absolut untuk disimpan di DB dan diakses kemudian
        file_path = user_dir / f"{doc_id}{Path(file.filename).suffix}"
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        chunks = load_and_split_document(str(file_path))
        if not chunks:
            continue

        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "INSERT INTO documents (id, username, filename, file_path, upload_date, file_size) VALUES (%s, %s, %s, %s, %s, %s)"
            values = (doc_id, username, file.filename, str(file_path.resolve()), datetime.now(), len(content))
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
        
        uploaded_docs_info.append({"id": doc_id, "filename": file.filename, "upload_date": datetime.now()})

    return {"uploaded_documents": uploaded_docs_info}

# PENTING: Mengubah route dari "" menjadi "/documents"
@router.get("/documents", response_model=list[DocumentInfo])
def get_documents(current_user: UserInDB = Depends(get_current_user)):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT id, filename, upload_date FROM documents WHERE username = %s ORDER BY upload_date DESC", (current_user.username,))
        docs_rows = cursor.fetchall()
        cursor.close()
        # PENTING: Mengubah setiap baris menjadi dictionary
        return [dict(row) for row in docs_rows]
