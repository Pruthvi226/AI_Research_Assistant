import re
from typing import List, Dict, Any

class CitationUtils:
    @staticmethod
    def extract_citations(text: str) -> List[int]:
        # Simple extraction of [1], [2] style citations
        matches = re.findall(r"\[(\d+)\]", text)
        return list(set([int(m) for m in matches]))

    @staticmethod
    def map_citations_to_sources(citations: List[int], sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mapped = []
        for c in citations:
            if c <= len(sources):
                mapped.append(sources[c-1])
        return mapped

    @staticmethod
    def format_with_citations(text: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        citations = CitationUtils.extract_citations(text)
        sources_metadata = CitationUtils.map_citations_to_sources(citations, sources)
        return {
            "text": text,
            "citations": sources_metadata
        }

citation_utils = CitationUtils()
