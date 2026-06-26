from typing import Any, Dict, Optional


class OrchestratorAgent:
    name = "Orchestrator Agent"

    KEYWORD_RULES = [
        ("podcast", "podcast", ["podcast", "audio", "voice explanation", "narration", "briefing"]),
        ("github", "github", ["github", "repo", "repository", "implementation"]),
        ("citation", "citations", ["citation", "reference", "related work", "bibliography", "cited"]),
        ("code", "code", ["code", "pytorch", "model", "training loop", "dataset loader", "scaffold"]),
        ("math", "equation", ["equation", "formula", "latex", "derive", "derivation", "loss function"]),
        ("research", "paper_analysis", ["summarize this paper", "summary", "paper", "methodology", "contribution"]),
        ("rag", "source_grounded_qa", ["ask from document", "source", "based on paper", "explain based on paper"]),
    ]

    AGENT_NAMES = {
        "research": "Research Paper Agent",
        "rag": "RAG Retrieval Agent",
        "math": "Math Equation Agent",
        "code": "Code Generation Agent",
        "citation": "Citation Agent",
        "github": "GitHub Repo Matcher Agent",
        "podcast": "Podcast Agent",
    }

    def __init__(self, agents: Dict[str, Any], db=None):
        self.agents = agents
        self.db = db

    def classify(self, query: str, payload: Optional[Dict[str, Any]] = None, session_id: str = "") -> Dict[str, str]:
        payload = payload or {}
        explicit = (payload.get("agent") or payload.get("agent_key") or "").strip().lower()
        if explicit:
            for key, name in self.AGENT_NAMES.items():
                if explicit in {key, name.lower()}:
                    return {"agent_key": key, "intent": self._intent_for_agent(key)}

        if payload.get("image_path") or payload.get("equation_image"):
            return {"agent_key": "math", "intent": "equation_reasoning"}
        if payload.get("file_type") == "pdf" or payload.get("uploaded_pdf"):
            return {"agent_key": "research", "intent": "paper_analysis"}

        lowered = (query or "").lower()
        for key, intent, keywords in self.KEYWORD_RULES:
            if any(keyword in lowered for keyword in keywords):
                return {"agent_key": key, "intent": intent}

        if session_id:
            return {"agent_key": "rag", "intent": "source_grounded_qa"}
        return {"agent_key": "research", "intent": "paper_analysis"}

    def run(self, query: str, session_id: str = "", payload: Optional[Dict[str, Any]] = None, **context: Any) -> Dict[str, Any]:
        payload = payload or {}
        route = self.classify(query, payload, session_id=session_id)
        agent_key = route["agent_key"]
        agent = self.agents.get(agent_key)
        if agent is None:
            raise ValueError(f"No agent is registered for route '{agent_key}'.")

        try:
            result = agent.run(query=query, session_id=session_id, **payload, **context)
            result.setdefault("selected_agent", self.AGENT_NAMES.get(agent_key, agent.name))
            result.setdefault("intent", route["intent"])
            result.setdefault("sources", [])
            result.setdefault("artifacts", {})
            status = "success"
        except Exception as exc:
            result = {
                "selected_agent": self.AGENT_NAMES.get(agent_key, "Unknown Agent"),
                "intent": route["intent"],
                "response": f"{result_error_prefix(agent_key)} {exc}",
                "sources": [],
                "artifacts": {"error": str(exc)},
            }
            status = "error"

        if self.db:
            try:
                self.db.log_agent(
                    selected_agent=result["selected_agent"],
                    intent=result["intent"],
                    query=query,
                    response=result.get("response", ""),
                    status=status,
                    metadata=result.get("artifacts", {}),
                )
            except Exception:
                pass
        return result

    @staticmethod
    def _intent_for_agent(agent_key: str) -> str:
        return {
            "research": "paper_analysis",
            "rag": "source_grounded_qa",
            "math": "equation_reasoning",
            "code": "ml_code_generation",
            "citation": "citation_analysis",
            "github": "github_repo_matching",
            "podcast": "podcast_generation",
        }.get(agent_key, "general_research")


def result_error_prefix(agent_key: str) -> str:
    return {
        "rag": "RAG retrieval failed:",
        "math": "Equation analysis failed:",
        "code": "Code generation failed:",
        "citation": "Citation analysis failed:",
        "github": "GitHub matching failed:",
        "podcast": "Podcast generation failed:",
        "research": "Research paper analysis failed:",
    }.get(agent_key, "Agent execution failed:")
