# file: app/api/routers/chat.py

from fastapi import APIRouter, Depends, HTTPException, status
import json
from datetime import datetime
from psycopg2.extras import DictCursor

from app.db.session import get_db_connection
from app.api.deps import get_current_user
from app.schemas.user import UserInDB
from app.services.rag_service import rag_service
from app.schemas.chat import ChatMessage, ChatResponse, ChatHistoryItem

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("", response_model=ChatResponse)
def process_chat_message(message: ChatMessage, current_user: UserInDB = Depends(get_current_user)):
    if not rag_service.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Sistem RAG tidak siap. Mohon coba lagi sesaat."
        )

    try:
        final_response = rag_service.invoke_chain(message.message, message.document_ids)
    except Exception as e:
        print(f"Error during RAG chain invocation: {e}")
        final_response = "Maaf, terjadi kesalahan saat memproses permintaan Anda. Silakan coba lagi."

    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            INSERT INTO chat_history 
            (session_id, username, message, response, document_ids) 
            VALUES (%s, %s, %s, %s, %s)
        """
        doc_ids_json = json.dumps(message.document_ids)
        values = (message.session_id, current_user.username, message.message, final_response, doc_ids_json)
        cursor.execute(query, values)
        conn.commit()
        cursor.close()

    return ChatResponse(response=final_response)

@router.get("/history/{session_id}", response_model=list[ChatHistoryItem])
def get_chat_session_history(session_id: str, current_user: UserInDB = Depends(get_current_user)):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        query = "SELECT message, response, timestamp FROM chat_history WHERE session_id = %s AND username = %s ORDER BY timestamp ASC"
        cursor.execute(query, (session_id, current_user.username))
        history = cursor.fetchall()
        cursor.close()
    
    formatted_history = []
    for row in history:
        formatted_history.append(ChatHistoryItem(sender="user", content=row["message"], timestamp=row["timestamp"]))
        formatted_history.append(ChatHistoryItem(sender="assistant", content=row["response"], timestamp=row["timestamp"]))
    
    return formatted_history
