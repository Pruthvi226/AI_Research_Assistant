import re
from pathlib import Path
from typing import Optional

from config import AUDIO_FOLDER


class AudioService:
    def __init__(self, output_folder: Optional[Path] = None):
        self.output_folder = Path(output_folder or AUDIO_FOLDER)
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def build_podcast_script(self, title: str, summary: str, document_text: str = "", llm_service=None) -> str:
        fallback = self._fallback_script(title, summary or document_text)
        if llm_service and llm_service.is_available:
            prompt = f"""Write a realistic spoken audio explanation for a research paper.

Style requirements:
- Write as natural narration for a curious student, like a friendly academic podcast host.
- Do not use markdown, code fences, headings, labels, bullet points, numbered lists, JSON, or stage directions.
- Do not say words like "section", "hash", "bullet", "colon", "backtick", "LaTeX", or "code block" unless the paper itself is about them.
- Avoid reading citations mechanically. Say "the authors" or "prior work" instead of bracketed references.
- Use smooth transitions: "Here is the big idea", "What makes this useful is", "A limitation to keep in mind is".
- Keep it concise, spoken, and human: around 90 to 140 seconds.
- Explain the paper in plain language first, then add the technical details.

Title: {title}
Summary or context:
{(summary or document_text)[:60000]}
"""
            return self._clean_for_speech(llm_service.generate_text(prompt, fallback=fallback))
        return fallback

    def generate_audio(self, script: str, session_id: str, overwrite: bool = True) -> Optional[str]:
        script = self._clean_for_speech(script)
        output_path = self.output_folder / f"{session_id}.mp3"
        script_path = self.output_folder / f"{session_id}_script.txt"
        script_path.write_text(script, encoding="utf-8")
        if output_path.exists() and not overwrite:
            return str(output_path)

        try:
            from gtts import gTTS

            gTTS(text=script, lang="en", tld="com", slow=False).save(str(output_path))
            return str(output_path)
        except Exception:
            return None

    @classmethod
    def _fallback_script(cls, title: str, summary: str) -> str:
        cleaned = " ".join((summary or "").split())[:1800]
        narrative = f"""Welcome to Scientia.ai. Today, let's make this research paper feel a little less intimidating.

The paper is titled {title}. The big idea is that the authors are trying to solve a specific research problem and show why their approach is useful. Instead of thinking of the paper as a wall of technical text, think of it as a story: there is a problem, there is a proposed method, there is evidence from experiments, and there are limits to what the method can prove.

Here is the plain-language version. {cleaned or "The authors propose an approach, evaluate it, and leave room for future improvement."}

Now, for the technical layer. The method should be understood through three questions. First, what data or inputs does it use? Second, what transformation or model does it apply? Third, how do the authors measure whether it worked? Those pieces tell us how strong the contribution is and where it might fail.

A limitation to keep in mind is that research results often depend on the dataset, the baselines, and the experimental setup. So the safest takeaway is this: the paper gives us a useful direction, but the idea becomes stronger when it is tested on broader data, compared with stronger alternatives, and reproduced carefully.

That is the core of the paper in human terms: what problem it tackles, how it tries to solve it, what evidence it gives, and what questions remain open."""
        return cls._clean_for_speech(narrative)

    @staticmethod
    def _clean_for_speech(text: str) -> str:
        """Remove markup and code-like formatting before sending text to TTS."""
        cleaned = text or ""
        cleaned = re.sub(r"```[\s\S]*?```", " ", cleaned)
        cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
        cleaned = cleaned.replace("**", "").replace("__", "")
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*\d+[\.\)]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*(hook|problem|method|results?|limitations?|takeaway|host\s*[ab]?|narrator)\s*:\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r"^\s*(hook|problem|method|results?|limitations?|takeaway)\s*$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r"\[(\d+)\]", r"reference \1", cleaned)
        cleaned = cleaned.replace("##", "")
        cleaned = re.sub(r"[#*_>{}\[\]|]+", " ", cleaned)
        cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        return cleaned.strip()
