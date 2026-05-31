from fastapi import APIRouter

router = APIRouter()

from app.services.rag_service import rag_service
from app.services.memory_service import memory_service

@router.post("/message")
async def chat_message(session_id: str, message: str):
    # Hybrid search in context
    context = rag_service.hybrid_search(message)
    response = f"AI response based on context: {context[:2]}..."
    
    await memory_service.add_chat_history(session_id, {"user": message, "ai": response})
    return {"response": response, "context": context}
