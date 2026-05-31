import os
import logging
from pathlib import Path
from typing import Optional
from gtts import gTTS
import google.generativeai as genai
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

        # If already cached/generated, return immediately
        if output_path.exists():
            logger.info(f"Podcast already cached at: {output_path}")
            return str(output_path)

        if not gemini.is_available:
            raise ValueError("Gemini API key is not configured. Add it in Settings.")

        logger.info(f"Generating technical audio script for: {doc_title}")

        prompt = f"""You are an elite academic audio host. Synthesize a highly engaging, professional, and clear vocal presentation of the following research paper.
        
        Write a complete, fluent narrative summarizing:
        1. The Core Breakthrough & Problem addressed.
        2. The Technical Methodology & Architecture used.
        3. The Evaluation Benchmarks & Experimental Results.
        4. Technical Limitations & Gaps for future work.

        Make your speech extremely articulate, logical, and structured. Use phrases like "Welcome to today's Scientia.ai audio briefing", "First, let's look at the methodology", "In terms of benchmarks, they evaluated...", and "Finally, a critical limitation is...".
        Do NOT write headers or host names (like "Host A:"). Write a single, cohesive, long technical narrative in natural speech.

        Research Paper Title: {doc_title}
        Research Paper Text:
        {full_text[:150000]}
        """

        try:
            model = genai.GenerativeModel(gemini.model_name)
            response = model.generate_content(prompt)
            narrative = response.text.strip()
            
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
