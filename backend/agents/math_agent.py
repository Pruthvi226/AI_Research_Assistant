import re
from typing import Any, Dict, Optional


class MathEquationAgent:
    name = "Math Equation Agent"

    def __init__(self, ocr_service=None, llm_service=None):
        self.ocr_service = ocr_service
        self.llm = llm_service

    def run(self, query: str = "", image_path: Optional[str] = None, **_: Any) -> Dict[str, Any]:
        equation_text = (query or "").strip()
        ocr_text = ""
        ocr_warning = ""
        if image_path and self.ocr_service:
            try:
                ocr_text = self.ocr_service.extract_text_from_image(image_path)
            except Exception as exc:
                if not equation_text:
                    raise
                ocr_warning = str(exc)
            equation_text = equation_text or ocr_text

        if not equation_text:
            raise ValueError("Provide equation text or upload an equation image.")

        if self.llm and self.llm.is_available:
            data = self._llm_equation(equation_text)
        else:
            data = self._fallback_equation(equation_text)
        data["ocr_text"] = ocr_text
        if ocr_warning:
            data["ocr_warning"] = ocr_warning

        response = (
            f"**Clean LaTeX:**\n$${data['latex']}$$\n\n"
            f"**Variables:**\n{data['variables']}\n\n"
            f"**Step-by-step explanation:**\n{data['explanation']}"
        )
        return {
            "selected_agent": self.name,
            "intent": "equation_reasoning",
            "response": response,
            "sources": [ocr_text] if ocr_text else [],
            "artifacts": data,
        }

    def _llm_equation(self, equation_text: str) -> Dict[str, str]:
        prompt = f"""Convert and explain this mathematical expression.
Return only valid JSON with keys: latex, variables, explanation.
Expression:
{equation_text}
"""
        fallback = self._fallback_equation(equation_text)
        try:
            data = self.llm.generate_json(prompt, fallback=fallback)
            return {
                "latex": str(data.get("latex") or fallback["latex"]),
                "variables": str(data.get("variables") or fallback["variables"]),
                "explanation": str(data.get("explanation") or fallback["explanation"]),
            }
        except Exception:
            return fallback

    @staticmethod
    def _fallback_equation(equation_text: str) -> Dict[str, str]:
        latex = equation_text.strip()
        replacements = {
            "alpha": r"\alpha",
            "beta": r"\beta",
            "gamma": r"\gamma",
            "lambda": r"\lambda",
            "sum": r"\sum",
            "sqrt": r"\sqrt",
            "->": r"\rightarrow",
            "*": r"\cdot ",
        }
        for raw, repl in replacements.items():
            latex = re.sub(rf"\b{re.escape(raw)}\b", lambda _match, value=repl: value, latex)
        variables = sorted(set(re.findall(r"\b[a-zA-Z]\w*\b", equation_text)))
        variables_text = ", ".join(variables) if variables else "No named variables were detected."
        explanation = (
            "The expression is treated as a mathematical relationship. Read the left side as the quantity being "
            "computed and the right side as the operations or terms that define it. For a deeper derivation, "
            "configure Gemini and resend the equation."
        )
        return {"latex": latex, "variables": variables_text, "explanation": explanation}
