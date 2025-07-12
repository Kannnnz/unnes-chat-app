# file: app/api/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, status
import shutil
from psycopg2.extras import DictCursor

from app.core import config
from app.db.session import get_db_connection
from app.api.deps import require_admin
from app.schemas.user import AdminStats, UserPublic
from app.schemas.document import DocumentDetail
from app.services.rag_service import rag_service

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])

@router.get("/stats", response_model=AdminStats)
def get_admin_stats():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_documents = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM chat_history")
        total_chats = cursor.fetchone()[0]
        cursor.close()
    return AdminStats(total_users=total_users, total_documents=total_documents, total_chats=total_chats)

@router.get("/users", response_model=list[UserPublic])
def get_all_users():
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC")
        users_rows = cursor.fetchall()
        cursor.close()
        # PENTING: Mengubah setiap baris menjadi dictionary
        return [dict(row) for row in users_rows]

@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(username: str, current_user: UserPublic = Depends(require_admin)):
    if username == current_user.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tidak dapat menghapus akun sendiri.")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pengguna '{username}' tidak ditemukan.")
        cursor.close()

    user_upload_dir = config.UPLOAD_DIR / username
    if user_upload_dir.exists():
        shutil.rmtree(user_upload_dir)
    
    rag_service.rebuild_index()
    return

@router.get("/documents", response_model=list[DocumentDetail])
def get_all_documents_for_admin():
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT id, username, filename, upload_date, file_size FROM documents ORDER BY upload_date DESC")
        documents_rows = cursor.fetchall()
        cursor.close()
        # PENTING: Mengubah setiap baris menjadi dictionary
        return [dict(row) for row in documents_rows]

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT file_path FROM documents WHERE id = %s", (document_id,))
        doc = cursor.fetchone()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokumen tidak ditemukan.")
        
        # PENTING: Gunakan Path() untuk memastikan path absolut
        file_to_delete = Path(doc["file_path"])
        if file_to_delete.exists():
            file_to_delete.unlink()
        
        cursor.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        conn.commit()
        cursor.close()

    rag_service.rebuild_index()
    return
