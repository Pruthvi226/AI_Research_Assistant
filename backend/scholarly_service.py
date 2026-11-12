import urllib.parse
import urllib.request
import json
import logging
import os
import re
import unicodedata
from functools import lru_cache
from difflib import SequenceMatcher
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def reconstruct_abstract(inverted_index: Optional[Dict[str, list]]) -> str:
    """
    Reconstruct the full abstract text from OpenAlex's inverted index representation.
    """
    if not inverted_index:
        return ""
    try:
        positions = {}
        for word, pos_list in inverted_index.items():
            for pos in pos_list:
                positions[pos] = word
        sorted_keys = sorted(positions.keys())
        sorted_words = [positions[i] for i in sorted_keys]
        return " ".join(sorted_words)
    except Exception as e:
        logger.error(f"Failed to reconstruct abstract: {e}")
        return ""

class ScholarlyService:
    """
    Service to query OpenAlex for citation metadata, abstract lookups,
    and academic metrics without requiring paid developer keys.
    """

    @staticmethod
    @lru_cache(maxsize=256)
    def search_paper_by_title(title: str) -> Optional[Dict[str, Any]]:
        """
        Query OpenAlex API for a paper by title and return citation counts,
        publication year, doi, and reconstructed abstract.
        """
        if not title or len(title.strip()) < 5:
            return None

        # Clean search query
        cleaned_query = title.strip().strip('"\'[]')
        encoded_query = urllib.parse.quote(cleaned_query)
        url = f"https://api.openalex.org/works?search={encoded_query}&limit=1"

        try:
            headers = {"User-Agent": "Scientia-Research/2.0"}
            if os.environ.get('OPENALEX_API_KEY'):
                headers['Authorization'] = f"Bearer {os.environ['OPENALEX_API_KEY']}"
            req = urllib.request.Request(
                url,
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
            results = data.get("results", [])
            if not results:
                logger.info(f"No scholarly results found for: {title}")
                return None

            work = results[0]
            abstract_index = work.get("abstract_inverted_index")
            abstract = reconstruct_abstract(abstract_index)

            # Extract authors
            authorships = work.get("authorships", [])
            author_names = [a.get("author", {}).get("display_name", "") for a in authorships if a.get("author")]
            author_str = ", ".join(author_names[:3])
            if len(author_names) > 3:
                author_str += " et al."

            return {
                "title": work.get("title", title),
                "authors": author_str,
                "year": work.get("publication_year"),
                "citations": work.get("cited_by_count", 0),
                "doi": work.get("doi"),
                "url": work.get("doi") or work.get("id"),
                "abstract": abstract if abstract else "Abstract not available in open-access registry."
                ,
                "openalex_id": work.get("id"),
                "related_works": work.get("related_works", [])[:20],
                "source": "OpenAlex",
            }
        except Exception as e:
            logger.error(f"OpenAlex lookup failed for title '{title}': {e}")
            return None

    @classmethod
    def resolve_reference(cls, raw_reference: str) -> Dict[str, Any]:
        """Resolve a bibliography entry only when its DOI or title matches evidence."""
        raw = " ".join((raw_reference or "").split()).strip()
        doi_match = re.search(
            r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", raw, flags=re.IGNORECASE
        )
        if doi_match:
            doi = doi_match.group(0).rstrip(".,;)")
            metadata = cls._lookup_crossref_doi(doi)
            if metadata:
                score = cls._title_similarity(raw, metadata.get("title", ""))
                return {
                    "metadata": metadata,
                    "resolution_status": "doi_match",
                    "verification_status": "unverified",
                    "matched_by": "doi",
                    "match_score": round(score, 3),
                    "metadata_title_matches_reference": score >= 0.6,
                }

        title = cls.extract_reference_title(raw)
        if len(title.split()) < 4:
            return {
                "metadata": None,
                "resolution_status": "unresolved",
                "verification_status": "unverified",
                "matched_by": None,
                "match_score": 0.0,
            }
        candidate = cls.search_paper_by_title(title)
        if not candidate:
            return {
                "metadata": None,
                "resolution_status": "unresolved",
                "verification_status": "unverified",
                "matched_by": None,
                "match_score": 0.0,
            }
        score = cls._title_similarity(title, candidate.get("title", ""))
        if score < 0.72:
            return {
                "metadata": None,
                "resolution_status": "unresolved",
                "verification_status": "unverified",
                "matched_by": None,
                "match_score": round(score, 3),
                "candidate_title": candidate.get("title"),
            }
        return {
            "metadata": candidate,
            "resolution_status": "title_candidate",
            "verification_status": "unverified",
            "matched_by": "title",
            "match_score": round(score, 3),
        }

    @staticmethod
    def extract_reference_title(reference: str) -> str:
        text = re.sub(r"^\s*(?:\[\d+\]|\d+[\.\)])\s*", "", reference or "")
        quoted = re.search(r"[“\"]([^”\"]{12,})[”\"]", text)
        if quoted:
            return quoted.group(1).strip()
        text = re.sub(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", "", text, flags=re.I)
        year = re.search(r"\((?:19|20)\d{2}[a-z]?\)\.?\s*(.+)$", text, flags=re.I)
        if year:
            text = year.group(1)
        else:
            year = re.search(r"\b(?:19|20)\d{2}[a-z]?\s*[,.;:]\s*(.+)$", text, flags=re.I)
            if year:
                text = year.group(1)
        parts = [part.strip(" ,.;:") for part in re.split(r"\.\s+", text) if part.strip(" ,.;:")]
        if not parts:
            return ""
        likely_title = max(parts, key=lambda part: len(re.findall(r"[A-Za-z]{3,}", part)))
        return likely_title[:300].strip()

    @staticmethod
    def _normalize_title(title: str) -> str:
        normalized = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode()
        return " ".join(re.findall(r"[a-z0-9]+", normalized.lower()))

    @classmethod
    def _title_similarity(cls, left: str, right: str) -> float:
        a = cls._normalize_title(left)
        b = cls._normalize_title(right)
        if not a or not b:
            return 0.0
        seq = SequenceMatcher(None, a, b).ratio()
        a_words, b_words = set(a.split()), set(b.split())
        overlap = len(a_words & b_words) / max(len(a_words | b_words), 1)
        if a in b or b in a:
            seq = max(seq, 0.85)
        return 0.65 * seq + 0.35 * overlap

    @staticmethod
    def _lookup_crossref_doi(doi: str) -> Optional[Dict[str, Any]]:
        url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "Scientia-Research/2.0"}
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                message = json.loads(response.read().decode()).get("message", {})
            title = (message.get("title") or [""])[0]
            if not title:
                return None
            authors = [
                " ".join(filter(None, (item.get("given"), item.get("family"))))
                for item in message.get("author", [])
            ]
            date_parts = (message.get("published") or {}).get("date-parts") or []
            year = date_parts[0][0] if date_parts and date_parts[0] else None
            return {
                "title": title,
                "authors": ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
                "year": year,
                "citations": message.get("is-referenced-by-count", 0),
                "doi": message.get("DOI") or doi,
                "url": f"https://doi.org/{message.get('DOI') or doi}",
                "abstract": message.get("abstract", ""),
                "source": "Crossref DOI",
            }
        except Exception as exc:
            logger.info("Crossref DOI resolution unavailable: %s", exc)
            return None

    @staticmethod
    def recommend_related_works(citations: list, limit: int = 8) -> list:
        related_to = {}
        for citation in citations:
            metadata = citation.get("scholarly") or {}
            for work_id in metadata.get("related_works", [])[:5]:
                openalex_id = str(work_id).rsplit("/", 1)[-1]
                if openalex_id.startswith("W"):
                    related_to.setdefault(openalex_id, citation.get("ref_num"))
        if not related_to:
            return []
        ids = "|".join(list(related_to)[:20])
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
            "filter": f"ids.openalex:{ids}",
            "per-page": str(min(limit, 8)),
        })
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "Scientia-Research/2.0"}
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                works = json.loads(response.read().decode()).get("results", [])
        except Exception as exc:
            logger.info("OpenAlex recommendations unavailable: %s", exc)
            return []
        recommendations = []
        for work in works[:limit]:
            title = work.get("title")
            if not title:
                continue
            doi = work.get("doi")
            recommendations.append({
                "title": title,
                "year": work.get("publication_year"),
                "citations": work.get("cited_by_count", 0),
                "doi": doi,
                "url": doi or work.get("id"),
                "related_to_ref": related_to.get(str(work.get("id", "")).rsplit("/", 1)[-1]),
                "provenance": "OpenAlex related works of a resolved bibliography candidate",
                "verification_status": "unverified_recommendation",
            })
        return recommendations
