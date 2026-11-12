import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class GitHubService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.last_search_status = "not_requested"
        self.last_search_error = ""

    def match_repositories(
        self,
        topic: str,
        repo_links: Optional[List[str]] = None,
        paper_links: Optional[List[str]] = None,
        paper_title: str = "",
        doi: str = "",
    ) -> List[Dict[str, Any]]:
        self.last_search_status = "ok"
        self.last_search_error = ""
        repos = []
        for link in repo_links or []:
            repo = self.summarize_repository_link(link, provenance="user_provided")
            if repo:
                repos.append(repo)
        for link in paper_links or []:
            repo = self.summarize_repository_link(link, provenance="paper_text")
            if repo:
                repos.append(repo)

        search_query = doi or paper_title or topic
        if search_query:
            candidates = self.search_repositories(search_query)
            for candidate in candidates[:3]:
                readme = self._readme_text(candidate.get("full_name", ""))
                if readme:
                    self._add_readme_evidence(
                        candidate, readme, paper_title or topic, doi
                    )
            repos.extend(candidates)

        deduped = {}
        for repo in repos:
            key = repo.get("full_name") or repo.get("html_url") or repo.get("name")
            if not key:
                continue
            current = deduped.get(key)
            if current is None or (
                repo.get("provenance") == "paper_text"
                or repo.get("provenance") == "user_provided"
            ):
                deduped[key] = repo
        ranked = sorted(
            deduped.values(),
            key=lambda item: item.get("relevance_score", 0),
            reverse=True,
        )
        return ranked[:8]

    def search_repositories(self, topic: str) -> List[Dict[str, Any]]:
        query = urllib.parse.urlencode({"q": topic, "per_page": 5})
        url = f"https://api.github.com/search/repositories?{query}"
        try:
            data = self._get_json(url)
        except Exception as exc:
            self._record_api_error(exc)
            return []
        items = data.get("items", [])
        return [self._normalize_repo(item, topic) for item in items]

    def summarize_repository_link(
        self, link: str, provenance: str = "user_provided"
    ) -> Optional[Dict[str, Any]]:
        parsed = urllib.parse.urlparse(link or "")
        if parsed.scheme not in {"https", "http"} or parsed.hostname not in {
            "github.com",
            "www.github.com",
        }:
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            return None
        owner, repo = parts[0], parts[1].removesuffix(".git")
        if not re.fullmatch(r"[A-Za-z0-9-]+", owner) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+", repo
        ):
            return None
        url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            data = self._get_json(url)
        except Exception as exc:
            self._record_api_error(exc)
            data = {
                "name": repo,
                "full_name": f"{owner}/{repo}",
                "html_url": f"https://github.com/{owner}/{repo}",
                "description": "Repository metadata could not be fetched from GitHub.",
            }
        normalized = self._normalize_repo(data, "")
        normalized["provenance"] = provenance
        normalized["relationship_status"] = (
            "paper_document_link_unverified"
            if provenance == "paper_text"
            else "user_provided_unverified"
        )
        normalized["match_evidence"] = (
            "The URL appears in the uploaded paper text; repository ownership and official status are not verified."
            if provenance == "paper_text"
            else "The URL was supplied by the user; its relationship to the paper is not verified."
        )
        return normalized

    def _get_json(self, url: str) -> Dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Scientia.ai",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))

    def _readme_text(self, full_name: str) -> str:
        if not full_name or "/" not in full_name:
            return ""
        try:
            result = self._get_json(f"https://api.github.com/repos/{full_name}/readme")
            content = result.get("content", "")
            if result.get("encoding") == "base64" and content:
                return base64.b64decode(content).decode(
                    "utf-8", errors="replace"
                )[:60000]
        except Exception as exc:
            self._record_api_error(exc)
        return ""

    def _record_api_error(self, exc: Exception) -> None:
        if isinstance(exc, urllib.error.HTTPError):
            if exc.code in {403, 429}:
                self.last_search_status = "rate_limited"
                self.last_search_error = (
                    "GitHub API rate limit reached. Retry later or configure an operator token."
                )
                return
            if exc.code == 404:
                self.last_search_status = "metadata_unavailable"
                return
        self.last_search_status = "upstream_unavailable"
        self.last_search_error = (
            "GitHub could not be reached. Candidate provenance may be incomplete."
        )

    @classmethod
    def _normalize_repo(cls, item: Dict[str, Any], topic: str) -> Dict[str, Any]:
        stars = int(item.get("stargazers_count") or 0)
        language = item.get("language") or "Mixed"
        description = item.get("description") or "No description provided."
        query_words = [
            word
            for word in re.findall(r"[a-z0-9]+", topic.lower())
            if len(word) > 2
        ]
        name_text = f"{item.get('full_name', '')} {item.get('name', '')}".lower()
        description_text = description.lower()
        name_matches = [word for word in query_words if word in name_text]
        description_matches = [
            word for word in query_words if word in description_text
        ]
        relevance = (
            0.65 * len(set(name_matches)) + 0.35 * len(set(description_matches))
        ) / max(len(set(query_words)), 1)
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
            "relevance_score": round(relevance, 3),
            "usefulness_score": round(relevance * 100),
            "relationship_status": "related_unverified",
            "provenance": "github_repository_search",
            "search_query": topic,
            "matched_terms": sorted(set(name_matches + description_matches)),
            "match_evidence": (
                "Repository name/description overlap: "
                + ", ".join(sorted(set(name_matches + description_matches))[:8])
                + ". Stars are not relevance evidence."
                if name_matches or description_matches
                else "Search candidate only; repository name and description do not confirm a paper match."
            ),
        }

    @staticmethod
    def _add_readme_evidence(
        candidate: Dict[str, Any], readme: str, paper_title: str, doi: str
    ) -> None:
        normalized = " ".join(re.findall(r"[a-z0-9]+", readme.lower()))
        title_terms = {
            word
            for word in re.findall(r"[a-z0-9]+", (paper_title or "").lower())
            if len(word) > 3
        }
        matched_title_terms = sorted(
            word for word in title_terms if f" {word} " in f" {normalized} "
        )
        doi_present = bool(doi and doi.lower() in normalized)
        coverage = len(matched_title_terms) / max(len(title_terms), 1)
        candidate["readme_evidence"] = {
            "available": True,
            "matched_title_terms": matched_title_terms[:12],
            "doi_mentioned": doi_present,
        }
        if doi_present or (len(matched_title_terms) >= 3 and coverage >= 0.4):
            candidate["match_evidence"] = (
                "The repository README mentions the paper DOI."
                if doi_present
                else "The repository README contains multiple title terms: "
                + ", ".join(matched_title_terms[:8])
                + "."
            )
            candidate["provenance"] = "github_readme_text_match"
            candidate["relevance_score"] = round(
                min(1.0, max(candidate["relevance_score"], 0.65 + coverage * 0.35)),
                3,
            )
            candidate["usefulness_score"] = round(
                candidate["relevance_score"] * 100
            )
