import urllib.parse
import urllib.request
import json
import logging
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
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Scientia.ai Academic Assistant/1.0 (mailto:assistant@scientia.ai)"}
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
            }
        except Exception as e:
            logger.error(f"OpenAlex lookup failed for title '{title}': {e}")
            return None
