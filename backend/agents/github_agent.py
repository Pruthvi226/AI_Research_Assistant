import re
from typing import Any, Dict, List, Optional


class GitHubRepoMatcherAgent:
    name = "GitHub Repo Matcher Agent"

    def __init__(self, github_service=None):
        self.github_service = github_service

    def run(
        self,
        query: str = "",
        repo_links: Optional[List[str]] = None,
        paper_title: str = "",
        filename: str = "",
        document_text: str = "",
        doi: str = "",
        **_: Any,
    ) -> Dict[str, Any]:
        topic = (query or "").strip()
        document_lines = [line.strip() for line in (document_text or "").splitlines() if line.strip()]
        title = paper_title.strip() or next(
            (line for line in document_lines[:12] if 5 < len(line) < 220),
            "",
        )
        if not title and filename:
            title = filename.rsplit(".", 1)[0].replace("_", " ")
        doi_match = re.search(
            r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
            f"{doi} {document_text}",
            flags=re.IGNORECASE,
        )
        doi = doi or (doi_match.group(0).rstrip(".,;") if doi_match else "")
        paper_links = list(dict.fromkeys(
            re.findall(
                r"https?://(?:www\.)?github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+",
                document_text or "",
                flags=re.IGNORECASE,
            )
        ))[:10]
        repos = []
        if self.github_service:
            repos = self.github_service.match_repositories(
                topic,
                repo_links=repo_links or [],
                paper_links=paper_links,
                paper_title=title,
                doi=doi,
            )

        status = getattr(self.github_service, "last_search_status", "not_requested")
        status_message = getattr(self.github_service, "last_search_error", "")
        response = self._format(repos, title or topic, status_message)
        return {
            "selected_agent": self.name,
            "intent": "github_repo_matching",
            "response": response,
            "sources": [repo.get("html_url", "") for repo in repos if repo.get("html_url")],
            "artifacts": {
                "repositories": repos,
                "mode": "github_metadata",
                "paper_title": title,
                "doi": doi or None,
                "api_status": status,
                "api_message": status_message,
            },
        }

    @staticmethod
    def _format(repos: List[Dict[str, Any]], topic: str, status_message: str = "") -> str:
        if not repos:
            message = (
                "No GitHub repositories could be matched right now. "
                "No result is treated as evidence that code does not exist."
            )
            return f"{message} {status_message}".strip()
        lines = [
            f"GitHub candidates for **{topic or 'the research topic'}**. "
            "Candidate ranking uses repository text and README matches, not popularity; "
            "no result is marked official or verified."
        ]
        for repo in repos[:5]:
            lines.append(
                f"- **{repo.get('name', 'repository')}** [{repo.get('relationship_status', 'unverified')}] "
                f"({repo.get('tech_stack', 'Unknown stack')}): "
                f"{repo.get('summary', repo.get('description', 'No summary available.'))} "
                f"Provenance: {repo.get('provenance', 'unknown')}. "
                f"Evidence: {repo.get('match_evidence', 'No match rationale available.')}"
            )
        if status_message:
            lines.append(f"\n{status_message}")
        return "\n".join(lines)
