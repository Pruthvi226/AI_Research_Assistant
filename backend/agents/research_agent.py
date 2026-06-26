import json
import re
from typing import Any, Dict, List, Optional


class ResearchPaperAgent:
    name = "Research Paper Agent"

    def __init__(self, llm_service=None):
        self.llm = llm_service

    def run(
        self,
        query: str = "",
        document_text: str = "",
        filename: str = "",
        summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        text = (document_text or "").strip()
        summary = summary or {}
        if self.llm and self.llm.is_available and text:
            structured = self._llm_analysis(text, filename)
        else:
            structured = self._fallback_analysis(text, summary)

        response = self._format_response(structured)
        return {
            "selected_agent": self.name,
            "intent": "paper_analysis",
            "response": response,
            "sources": [],
            "artifacts": {"analysis": structured},
        }

    def _llm_analysis(self, text: str, filename: str) -> Dict[str, str]:
        prompt = f"""Analyze this research paper for a student researcher.
Return only valid JSON with these string keys:
problem_statement, main_contribution, methodology, dataset_used, results,
limitations, future_scope, beginner_summary.

Paper title or filename: {filename}
Paper text:
{text[:120000]}
"""
        fallback = self._fallback_analysis(text, {})
        try:
            data = self.llm.generate_json(prompt, fallback=fallback)
            return {key: str(data.get(key) or fallback[key]) for key in fallback}
        except Exception:
            return fallback

    def _fallback_analysis(self, text: str, summary: Dict[str, Any]) -> Dict[str, str]:
        abstract = summary.get("abstract") or self._first_sentences(text, 4)
        sections = summary.get("sections") or {}
        methodology = sections.get("Methodology") or self._find_sentences(text, ["method", "model", "approach", "algorithm"], 3)
        results = sections.get("Experiments & Results") or self._find_sentences(text, ["result", "accuracy", "performance", "outperform", "benchmark"], 3)
        limitations = self._find_sentences(text, ["limitation", "future work", "threat", "constraint"], 2)
        dataset = self._find_sentences(text, ["dataset", "data set", "corpus", "benchmark"], 2)
        contribution = self._find_sentences(text, ["contribution", "propose", "novel", "introduce"], 3)

        return {
            "problem_statement": self._clean(abstract) or "The paper's problem statement could not be confidently extracted.",
            "main_contribution": self._clean(contribution) or "The core contribution appears to be a proposed method or analysis described in the paper.",
            "methodology": self._clean(methodology) or "Methodology details were not clearly detected in the extracted text.",
            "dataset_used": self._clean(dataset) or "No explicit dataset name was detected in the available text.",
            "results": self._clean(results) or "Results were not clearly detected in the available text.",
            "limitations": self._clean(limitations) or "No explicit limitations section was detected.",
            "future_scope": self._find_sentences(text, ["future", "extend", "improve"], 2) or "Future work can build on the paper by validating the method on broader data and stronger baselines.",
            "beginner_summary": self._clean(abstract) or "This paper studies a research problem, proposes a method, evaluates it, and discusses its implications.",
        }

    @staticmethod
    def _format_response(data: Dict[str, str]) -> str:
        labels = [
            ("Problem statement", "problem_statement"),
            ("Main contribution", "main_contribution"),
            ("Methodology", "methodology"),
            ("Dataset used", "dataset_used"),
            ("Results", "results"),
            ("Limitations", "limitations"),
            ("Future scope", "future_scope"),
            ("Beginner-friendly summary", "beginner_summary"),
        ]
        return "\n\n".join(f"**{label}:**\n{data.get(key, '').strip()}" for label, key in labels)

    @staticmethod
    def _sentences(text: str) -> List[str]:
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", (text or "").replace("\n", " "))
            if sentence.strip()
        ]

    def _first_sentences(self, text: str, limit: int) -> str:
        return " ".join(self._sentences(text)[:limit])

    def _find_sentences(self, text: str, keywords: List[str], limit: int) -> str:
        lowered_keywords = [k.lower() for k in keywords]
        matches = []
        for sentence in self._sentences(text):
            lowered = sentence.lower()
            if any(keyword in lowered for keyword in lowered_keywords):
                matches.append(sentence)
            if len(matches) >= limit:
                break
        return " ".join(matches)

    @staticmethod
    def _clean(text: str, limit: int = 900) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[:limit].rsplit(" ", 1)[0].strip() + "..."
