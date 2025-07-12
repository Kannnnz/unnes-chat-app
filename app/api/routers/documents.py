from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from typing import List
import uuid
from pathlib import Path
from datetime import datetime 
from psycopg2.extras import DictCursor


from app.core import config
from app.db.session import get_db_connection
from app.api.deps import get_current_user
from app.services.rag_service import rag_service, load_and_split_document

router = APIRouter()

@router.post("/upload", tags=["Documents"])
async def upload_documents(files: List[UploadFile] = File(...), current_user: dict = Depends(get_current_user)):
    if not rag_service.is_ready:
        raise HTTPException(status_code=503, detail="Sistem RAG tidak siap.")
    
    username = current_user['username']
    user_dir = config.UPLOAD_DIR / username
    user_dir.mkdir(exist_ok=True)
    uploaded_docs_info = []

    for file in files:
        doc_id = str(uuid.uuid4())
        file_path = user_dir / f"{doc_id}{Path(file.filename).suffix}"
        
        try:
            content = await file.read()
            with open(file_path, "wb") as f: f.write(content)
            
            chunks = load_and_split_document(file_path)
            if not chunks: 
                # Hapus file jika tidak bisa diproses
                file_path.unlink()
                continue

            for chunk in chunks:
                chunk.metadata.update({"doc_id": doc_id, "filename": file.filename, "owner": username})
            
            rag_service.add_documents_to_index(chunks)

            with get_db_connection() as conn:
                cursor = conn.cursor()
                query = "INSERT INTO documents (id, username, filename, file_path, upload_date, file_size, is_indexed) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                values = (doc_id, username, file.filename, str(file_path), datetime.now(), len(content), 1)
                cursor.execute(query, values)
                conn.commit()
                cursor.close()
            
            uploaded_docs_info.append({"document_id": doc_id, "filename": file.filename})

        except Exception as e:
            # Jika terjadi error, hapus file yang mungkin sudah terbuat
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Gagal memproses file {file.filename}: {e}")

    return {"uploaded_documents": uploaded_docs_info}

@router.get("/documents", tags=["Documents"])
def get_documents(current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        if current_user['role'] == 'admin':
            cursor.execute("SELECT id, username, filename, upload_date FROM documents ORDER BY upload_date DESC")
        else:
            cursor.execute("SELECT id, filename, upload_date FROM documents WHERE username = %s ORDER BY upload_date DESC", (current_user['username'],))
        docs = cursor.fetchall()
        cursor.close()
    return {"documents": docs}
