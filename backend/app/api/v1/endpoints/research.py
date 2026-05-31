from fastapi import APIRouter

router = APIRouter()

from app.services.agent_service import agent_service

@router.post("/query")
async def perform_research(query: str):
    result = await agent_service.run_research_pipeline(query)
    return {"research_result": result}
