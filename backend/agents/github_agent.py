from typing import Any, Dict, List, Optional


class GitHubRepoMatcherAgent:
    name = "GitHub Repo Matcher Agent"

    def __init__(self, github_service=None):
        self.github_service = github_service

    def run(self, query: str = "", repo_links: Optional[List[str]] = None, **_: Any) -> Dict[str, Any]:
        topic = (query or "").strip()
        repos = []
        if self.github_service:
            repos = self.github_service.match_repositories(topic, repo_links=repo_links or [])

        response = self._format(repos, topic)
        return {
            "selected_agent": self.name,
            "intent": "github_repo_matching",
            "response": response,
            "sources": [repo.get("html_url", "") for repo in repos if repo.get("html_url")],
            "artifacts": {"repositories": repos},
        }

    @staticmethod
    def _format(repos: List[Dict[str, Any]], topic: str) -> str:
        if not repos:
            return (
                "No GitHub repositories could be matched right now. "
                "If the GitHub API is unavailable, paste repository links directly and retry."
            )
        lines = [f"Top repositories for **{topic or 'the research topic'}**:"]
        for repo in repos[:5]:
            lines.append(
                f"- **{repo.get('name', 'repository')}** ({repo.get('tech_stack', 'Unknown stack')}): "
                f"{repo.get('summary', repo.get('description', 'No summary available.'))} "
                f"Usefulness: {repo.get('usefulness_score', 'n/a')}/100"
            )
        return "\n".join(lines)
