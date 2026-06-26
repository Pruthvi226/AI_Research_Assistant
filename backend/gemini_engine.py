import json
import logging
from typing import Dict, Any, List, Optional
from config import AIConfig

logger = logging.getLogger(__name__)
genai = None


def _load_genai():
    global genai
    if genai is None:
        import google.generativeai as loaded_genai
        genai = loaded_genai
    return genai


def _clean_json_text(text: str) -> str:
    cleaned_text = text.strip()
    if cleaned_text.startswith("```"):
        lines = cleaned_text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned_text = "\n".join(lines).strip()
        if cleaned_text.startswith("json"):
            cleaned_text = cleaned_text[4:].strip()
    return cleaned_text

class GeminiEngine:
    """
    Advanced AI Engine using Google Gemini API to extract detailed summaries,
    complex research insights, and perform long-context QA on research documents.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini engine.
        
        Args:
            api_key: Optional API key. Fallback to AIConfig or environment.
        """
        self.api_key = api_key or AIConfig.GEMINI_API_KEY
        self.model_name = AIConfig.GEMINI_MODEL
        self._configured = False
        self._init_client()

    @staticmethod
    def is_valid_api_key(api_key: Optional[str]) -> bool:
        """Reject blank/template keys before expensive cloud calls are attempted."""
        key = (api_key or "").strip()
        if not key:
            return False
        lowered = key.lower()
        invalid_markers = (
            "...",
            "your_",
            "your-",
            "your ",
            "placeholder",
            "change_me",
            "change-in-production",
            "example",
        )
        return not any(marker in lowered for marker in invalid_markers)

    @staticmethod
    def mask_api_key(api_key: Optional[str]) -> str:
        key = (api_key or "").strip()
        if not GeminiEngine.is_valid_api_key(key):
            return ""
        return f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "********"

    def _init_client(self):
        """Configure the genai client if a key is available."""
        if self.is_valid_api_key(self.api_key):
            try:
                _load_genai().configure(api_key=self.api_key)
                self._configured = True
            except Exception as e:
                logger.error(f"Failed to configure Gemini client: {e}")
                self._configured = False
        else:
            self._configured = False

    @property
    def is_available(self) -> bool:
        """Return True if the Gemini API client is configured successfully."""
        return self._configured

    def generate_text(self, prompt: str, json_mode: bool = False) -> str:
        """Generate raw text from Gemini, optionally requesting JSON mode."""
        if not self.is_available:
            raise ValueError("Gemini API key is not configured. Please supply a valid API key in Settings.")
        try:
            model = _load_genai().GenerativeModel(self.model_name)
            kwargs = {}
            if json_mode:
                kwargs["generation_config"] = {"response_mime_type": "application/json"}
            response = model.generate_content(prompt, **kwargs)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise ValueError(f"Gemini generation failed: {str(e)}")

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        """Generate JSON and parse it defensively."""
        cleaned_text = _clean_json_text(self.generate_text(prompt, json_mode=True))
        return json.loads(cleaned_text)

    def generate_summary_and_insights(self, text: str) -> Dict[str, Any]:
        """
        Generate full paper summary and advanced research insights using a single Gemini API call.
        Uses JSON mode for robust structured output.
        """
        if not self.is_available:
            raise ValueError("Gemini API key is not configured. Please supply a valid API key in Settings.")

        prompt = f"""You are a state-of-the-art AI Research Assistant. Your task is to analyze the following research paper text and extract high-quality, comprehensive, and precise summaries and academic insights.
        
        Generate your response in EXACTLY the following JSON format:
        {{
            "abstract": "A clear, concise, and professional synthesis of the entire paper's core thesis, problem, methodology, results, and implications.",
            "sections": {{
                "Introduction": "Summary of the context, problem, and background.",
                "Methodology": "Summary of the core approach, architecture, or research methods.",
                "Experiments & Results": "Summary of evaluations, findings, and key performance metrics.",
                "Conclusion & Future Work": "Summary of conclusions and primary takeaways."
            }},
            "key_contributions": [
                "Detailed bullet point describing contribution 1.",
                "Detailed bullet point describing contribution 2.",
                "Detailed bullet point describing contribution 3."
            ],
            "limitations": [
                "Detailed bullet point describing limitation 1.",
                "Detailed bullet point describing limitation 2."
            ],
            "future_research": [
                "Detailed academic direction for future work 1.",
                "Detailed academic direction for future work 2."
            ],
            "research_gaps": [
                "Identified gap in literature/approach 1.",
                "Identified gap in literature/approach 2."
            ],
            "suggested_titles": [
                "Concise follow-up academic title 1",
                "Concise follow-up academic title 2"
            ],
            "important_sentences": [
                "Direct quote or critical sentence from the paper highlighting key definitions or findings.",
                "Another critical quote highlighting performance metrics or key thesis."
            ],
            "tables": [
                {{
                    "title": "Title or Caption of the Table detected in the text (e.g. Table 1: Model Accuracy)",
                    "markdown": "A perfect transcription of the tabular data formatted as a standard GitHub Flavored Markdown table."
                }}
            ],
            "equations": [
                {{
                    "title": "Short descriptive name of the mathematical equation or formula",
                    "latex": "Valid clean LaTeX code representation of the formula (e.g. Loss = \\\\alpha \\\\cdot L_{{sim}} + (1 - \\\\alpha) \\\\cdot L_{{reg}}). Use double backslashes for LaTeX macros in string literals.",
                    "description": "Clear technical explanation of what this equation calculates and its academic significance in the paper.",
                    "variables": [
                        {{
                            "name": "Exact variable character name used in js_expression (e.g. alpha)",
                            "label": "Human readable label (e.g. Similarity Coefficient)",
                            "min": 0,
                            "max": 1,
                            "step": 0.05,
                            "default": 0.5,
                            "description": "Explanatory variable description"
                        }}
                    ],
                    "js_expression": "Clean mathematical JavaScript expression string mapping the variables (e.g. alpha * L_sim + (1 - alpha) * L_reg)"
                }}
            ]
        }}

        Do NOT add any markdown formatting (like ```json ... ```) or conversational preamble. Return ONLY the raw valid JSON string.

        Research Paper Text:
        {text[:300000]}
        """

        try:
            return self.generate_json(prompt)
        except Exception as e:
            logger.error(f"Failed to generate summaries via Gemini: {e}")
            raise ValueError(f"Failed to analyze paper via Gemini: {str(e)}")

    def answer_question(self, question: str, context: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate a QA answer using the paper's context and conversation history.
        """
        if not self.is_available:
            raise ValueError("Gemini API key is not configured. Please supply a valid API key in Settings.")

        history_str = ""
        if history:
            history_str = "Conversation History:\n"
            for h in history:
                role = "User" if h.get("role") == "user" else "Assistant"
                # Support both 'content' and 'text' keys
                content = h.get("content") or h.get("text") or ""
                history_str += f"{role}: {content}\n"
            history_str += "\n"

        prompt = f"""You are a professional AI Research Assistant. Answer the user's question about the research paper using the provided paper context.
        Provide a detailed, well-structured, and technically precise answer. Refer directly to the evidence in the paper text. 
        If the answer cannot be found in the context, use your general research knowledge but explicitly state that it is inferred.

        {history_str}
        Research Paper Context:
        {context}

        Question:
        {question}

        Answer:
        """

        try:
            return self.generate_text(prompt)
        except Exception as e:
            logger.error(f"Failed to answer question via Gemini: {e}")
            raise ValueError(f"Failed to answer question via Gemini: {str(e)}")
