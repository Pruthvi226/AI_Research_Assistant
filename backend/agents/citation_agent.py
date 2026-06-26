import re
from typing import Any, Dict, List, Optional


class CitationAgent:
    name = "Citation Agent"

    def __init__(self, scholarly_service=None, llm_service=None):
        self.scholarly_service = scholarly_service
        self.llm = llm_service

    def run(
        self,
        query: str = "",
        document_text: str = "",
        references: Optional[Dict[str, str]] = None,
        ref_num: Optional[str] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        references = references or self._extract_references(document_text)
        if ref_num:
            references = {ref_num: references.get(str(ref_num), "")}

        citations = []
        for key, raw in list(references.items())[:20]:
            if not raw:
                continue
            details = None
            if self.scholarly_service:
                try:
                    details = self.scholarly_service.search_paper_by_title(raw)
                except Exception:
                    details = None
            citations.append({
                "ref_num": key,
                "raw_text": raw,
                "summary": self._summarize_reference(raw, details),
                "scholarly": details or {},
            })

        themes = self._themes(citations)
        response = self._format(citations, themes)
        return {
            "selected_agent": self.name,
            "intent": "citation_analysis",
            "response": response,
            "sources": [item["raw_text"] for item in citations[:5]],
            "artifacts": {"citations": citations, "themes": themes},
        }

    @staticmethod
    def _extract_references(text: str) -> Dict[str, str]:
        refs = {}
        pattern = re.compile(r"(?:\[(\d+)\]|^\s*(\d+)[\.\)]\s+)(.*?)(?=\n\s*(?:\[\d+\]|\d+[\.\)])|\Z)", re.M | re.S)
        for match in pattern.finditer(text or ""):
            key = match.group(1) or match.group(2)
            body = re.sub(r"\s+", " ", match.group(3)).strip()
            if key and body:
                refs[key] = body
        return refs

    @staticmethod
    def _summarize_reference(raw: str, details: Optional[Dict[str, Any]]) -> str:
        if details and details.get("abstract"):
            abstract = details["abstract"]
            return abstract[:350] + ("..." if len(abstract) > 350 else "")
        return raw[:280] + ("..." if len(raw) > 280 else "")

    @staticmethod
    def _themes(citations: List[Dict[str, Any]]) -> List[str]:
        text = " ".join(item["raw_text"].lower() for item in citations)
        themes = []
        for keyword, label in (
            ("transformer", "Transformer and attention models"),
            ("graph", "Graph learning"),
            ("retrieval", "Retrieval augmented methods"),
            ("vision", "Computer vision"),
            ("language", "Language modeling"),
            ("optimization", "Optimization and training"),
            ("dataset", "Dataset and benchmark design"),
        ):
            if keyword in text:
                themes.append(label)
        return themes or ["General related work and methodological background"]

    @staticmethod
    def _format(citations: List[Dict[str, Any]], themes: List[str]) -> str:
        if not citations:
            return "No references were detected in the available document text."
        lines = ["**Related work themes:** " + ", ".join(themes), ""]
        for item in citations[:8]:
            lines.append(f"- [{item['ref_num']}] {item['summary']}")
        return "\n".join(lines)
