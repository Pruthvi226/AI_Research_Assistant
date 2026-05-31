from fastapi import APIRouter
from app.api.v1.endpoints import research, documents, chat, auth

api_router = APIRouter()
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
