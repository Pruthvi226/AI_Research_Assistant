from typing import List, Dict, Any
import asyncio
from app.services.search_service import search_service
from app.services.rag_service import rag_service

class AgentService:
    @staticmethod
    async def planner_agent(query: str) -> List[str]:
        # Decomposes the query into sub-questions (placeholder for LLM call)
        # In production, use LangChain/OpenAI to generate sub-queries
        return [
            f"Core concepts of {query}",
            f"Recent advancements in {query}",
            f"Practical applications of {query}"
        ]

    @staticmethod
    async def research_agent(sub_queries: List[str]) -> List[Dict[str, Any]]:
        tasks = [search_service.search_tavily(sq) for sq in sub_queries]
        results = await asyncio.gather(*tasks)
        return [{"query": q, "results": r} for q, r in zip(sub_queries, results)]

    @staticmethod
    async def critic_agent(research_results: List[Dict[str, Any]]) -> bool:
        # Verifies correctness and relevance (placeholder)
        return True

    @staticmethod
    async def writer_agent(query: str, research_data: List[Dict[str, Any]]) -> str:
        # Generates a structured response (placeholder for LLM)
        summary = f"Summary of research for: {query}\n\n"
        for item in research_data:
            summary += f"### {item['query']}\n"
            for res in item['results']:
                summary += f"- {res.get('title')}: {res.get('url')}\n"
        return summary

    @staticmethod
    async def run_research_pipeline(query: str) -> str:
        sub_queries = await AgentService.planner_agent(query)
        research_data = await AgentService.research_agent(sub_queries)
        is_valid = await AgentService.critic_agent(research_data)
        
        if is_valid:
            return await AgentService.writer_agent(query, research_data)
        else:
            return "Research failed validation."

agent_service = AgentService()
