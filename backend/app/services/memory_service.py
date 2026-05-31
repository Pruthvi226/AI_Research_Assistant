import redis.asyncio as redis
from typing import List, Dict, Any, Optional
import json
from app.core.config import settings

class MemoryService:
    def __init__(self):
        self.redis = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

    async def add_chat_history(self, session_id: str, message: Dict[str, Any]):
        history = await self.redis.get(f"chat_history:{session_id}")
        if history:
            history = json.loads(history)
        else:
            history = []
        
        history.append(message)
        # Keep only the last 20 messages for short-term memory
        history = history[-20:]
        await self.redis.set(f"chat_history:{session_id}", json.dumps(history), ex=3600 * 24) # 24h expiry

    async def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        history = await self.redis.get(f"chat_history:{session_id}")
        return json.loads(history) if history else []

    async def add_long_term_memory(self, user_id: int, interaction: Dict[str, Any]):
        # This would involve adding an entry to a user-specific vector store
        # For now, let's keep it abstract
        pass

memory_service = MemoryService()
