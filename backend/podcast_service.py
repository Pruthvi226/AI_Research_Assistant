import os
import logging
import re
from pathlib import Path
from typing import Optional
from gtts import gTTS
from config import UPLOAD_FOLDER
from gemini_engine import GeminiEngine

logger = logging.getLogger(__name__)

class PodcastService:
    """
    Generates dynamic audio narrative summaries (NotebookLM style)
    of research papers using Gemini API and Google Text-to-Speech (gTTS).
    """

    @staticmethod
    def generate_audio_overview(session_id: str, doc_title: str, full_text: str, gemini: GeminiEngine) -> Optional[str]:
        """
        Synthesize a highly engaging audio overview.
        Saves as uploads/<session_id>_podcast.mp3 and returns file path.
        """
        output_path = UPLOAD_FOLDER / f"{session_id}_podcast.mp3"

        if not gemini.is_available:
            raise ValueError("Gemini API key is not configured. Add it in Settings.")

        logger.info(f"Generating technical audio script for: {doc_title}")

        prompt = f"""You are an elite academic audio host. Synthesize a realistic, professional, and clear spoken explanation of the following research paper.
        
        Write a single cohesive narration that sounds like a friendly research podcast host explaining the paper to a curious student.
        Do not write markdown, headings, bullet points, numbered lists, host names, stage directions, JSON, code, code fences, or labels.
        Do not mechanically read citations or equations. Paraphrase them naturally.
        Explain the paper in this order, but without section headings: the big problem, the main idea, how the method works, what the experiments show, one important limitation, and the practical takeaway.
        Use warm transitions like "Here is the big idea", "What makes this interesting is", and "A limitation to keep in mind is".

        Research Paper Title: {doc_title}
        Research Paper Text:
        {full_text[:150000]}
        """

        try:
            narrative = PodcastService.clean_for_speech(gemini.generate_text(prompt))
            
            if not narrative:
                raise ValueError("Failed to generate narrative script from LLM.")

            logger.info("Narrative script generated. Compiling Text-to-Speech...")
            
            # Synthesize voice using gTTS (high-quality American English accent)
            tts = gTTS(text=narrative, lang='en', tld='com', slow=False)
            
            # Save audio
            tts.save(str(output_path))
            logger.info(f"Vocal summary saved at: {output_path}")
            
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to generate audio overview: {e}")
            raise e

    @staticmethod
    def clean_for_speech(text: str) -> str:
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
        cleaned = re.sub(r"[#*_>{}\[\]|]+", " ", cleaned)
        cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        return cleaned.strip()
