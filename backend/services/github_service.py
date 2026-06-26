import base64
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class GitHubService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")

    def match_repositories(self, topic: str, repo_links: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        repos = []
        for link in repo_links or []:
            repo = self.summarize_repository_link(link)
            if repo:
                repos.append(repo)

        if topic:
            repos.extend(self.search_repositories(topic))

        deduped = {}
        for repo in repos:
            key = repo.get("full_name") or repo.get("html_url") or repo.get("name")
            if key and key not in deduped:
                deduped[key] = repo
        ranked = sorted(deduped.values(), key=lambda item: item.get("usefulness_score", 0), reverse=True)
        return ranked[:8]

    def search_repositories(self, topic: str) -> List[Dict[str, Any]]:
        query = urllib.parse.quote(f"{topic} machine learning")
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=5"
        try:
            data = self._get_json(url)
        except Exception:
            return []
        items = data.get("items", [])
        return [self._normalize_repo(item, topic) for item in items]

    def summarize_repository_link(self, link: str) -> Optional[Dict[str, Any]]:
        match = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", link or "")
        if not match:
            return None
        owner, repo = match.group(1), match.group(2).replace(".git", "")
        url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            data = self._get_json(url)
        except Exception:
            return {
                "name": repo,
                "full_name": f"{owner}/{repo}",
                "html_url": f"https://github.com/{owner}/{repo}",
                "description": "Repository metadata could not be fetched from GitHub.",
                "summary": "Metadata unavailable. Check the repository manually.",
                "tech_stack": "Unknown",
                "usefulness_score": 40,
            }
        return self._normalize_repo(data, "")

    def _get_json(self, url: str) -> Dict[str, Any]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "Scientia.ai"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _normalize_repo(item: Dict[str, Any], topic: str) -> Dict[str, Any]:
        stars = int(item.get("stargazers_count") or 0)
        language = item.get("language") or "Mixed"
        description = item.get("description") or "No description provided."
        score = min(100, 35 + min(stars, 5000) // 100 + (10 if topic and topic.lower() in description.lower() else 0))
        return {
            "id": item.get("id"),
            "name": item.get("name") or item.get("full_name"),
            "full_name": item.get("full_name"),
            "html_url": item.get("html_url"),
            "description": description,
            "summary": description,
            "language": language,
            "stargazers_count": stars,
            "stars": stars,
            "tech_stack": language,
            "usefulness_score": score,
        }
