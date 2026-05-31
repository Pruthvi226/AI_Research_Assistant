import httpx
from typing import List, Dict, Any
from app.core.config import settings

class SearchService:
    def __init__(self):
        self.tavily_api_key = settings.TAVILY_API_KEY

    async def search_tavily(self, query: str, search_depth: str = "advanced") -> List[Dict[str, Any]]:
        if not self.tavily_api_key:
            return [{"error": "Tavily API key not configured"}]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": search_depth,
                    "max_results": 5
                }
            )
            data = response.json()
            return data.get("results", [])

search_service = SearchService()
