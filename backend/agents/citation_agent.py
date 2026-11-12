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
        document_title: str = "Uploaded paper",
        reference_pages: Optional[Dict[str, int]] = None,
        ref_num: Optional[str] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        references = references or self._extract_references(document_text)
        reference_pages = reference_pages or {}
        if ref_num:
            references = {ref_num: references.get(str(ref_num), "")}

        citations = []
        for index, (key, raw) in enumerate(list(references.items())[:30]):
            if not raw:
                continue
            details = None
            resolution = {}
            if self.scholarly_service and index < 5:
                try:
                    if hasattr(self.scholarly_service, "resolve_reference"):
                        resolution = self.scholarly_service.resolve_reference(raw)
                        details = resolution.get("metadata")
                    elif len(citations) < 3:
                        details = self.scholarly_service.search_paper_by_title(raw)
                        if details:
                            resolution = {
                                "resolution_status": "metadata_candidate",
                                "verification_status": "unverified",
                                "matched_by": "legacy_title_search",
                                "match_score": None,
                            }
                except Exception:
                    details = None
            elif index >= 5:
                resolution = {
                    "resolution_status": "not_checked",
                    "verification_status": "unverified",
                }
            citations.append({
                "ref_num": key,
                "source_page": reference_pages.get(str(key)),
                "raw_text": raw,
                "summary": self._summarize_reference(raw, details),
                "scholarly": details or {},
                "verification_status": "unverified",
                "resolution_status": resolution.get(
                    "resolution_status", "unresolved"
                ),
                "matched_by": resolution.get("matched_by"),
                "match_score": resolution.get("match_score"),
                "candidate_title": resolution.get("candidate_title"),
            })

        themes = self._themes(citations)
        response = self._format(citations, themes)
        graph = {
            "nodes": [
                {
                    "id": "source-paper",
                    "label": document_title,
                    "type": "uploaded_paper",
                    "verification_status": "source_document",
                },
                *[
                    {
                        "id": f"reference-{item['ref_num']}",
                        "label": (
                            item.get("scholarly", {}).get("title")
                            or item.get("candidate_title")
                            or item["raw_text"][:160]
                        ),
                        "type": "resolved_candidate" if item.get("scholarly") else "unresolved_reference",
                        "ref_num": item["ref_num"],
                        "verification_status": "unverified",
                    }
                    for item in citations
                ],
            ],
            "edges": [
                {
                    "source": "source-paper",
                    "target": f"reference-{item['ref_num']}",
                    "kind": "cites",
                    "evidence": item["raw_text"],
                    "source_page": item.get("source_page"),
                    "resolution_status": item["resolution_status"],
                }
                for item in citations
            ],
        }
        recommendations = []
        if self.scholarly_service and hasattr(self.scholarly_service, "recommend_related_works"):
            try:
                recommendations = self.scholarly_service.recommend_related_works(citations)
            except Exception:
                recommendations = []
        return {
            "selected_agent": self.name,
            "intent": "citation_analysis",
            "response": response,
            "sources": [item["raw_text"] for item in citations[:5]],
            "artifacts": {
                "citations": citations,
                "themes": themes,
                "graph": graph,
                "recommendations": recommendations,
                "mode": "metadata_extraction",
            },
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
            resolution = item.get("resolution_status")
            status = (
                "DOI metadata match; relationship unverified"
                if resolution == "doi_match"
                else "title candidate; relationship unverified"
                if resolution == "title_candidate"
                else "metadata candidate; verify manually"
                if resolution == "metadata_candidate"
                else "not checked; resolution limit reached"
                if resolution == "not_checked"
                else "unresolved; not verified"
            )
            lines.append(f"- [{item['ref_num']}] {item['summary']} ({status})")
        return "\n".join(lines)
