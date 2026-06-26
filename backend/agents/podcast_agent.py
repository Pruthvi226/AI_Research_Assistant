from typing import Any, Dict


class PodcastAgent:
    name = "Podcast Agent"

    def __init__(self, audio_service=None, llm_service=None):
        self.audio_service = audio_service
        self.llm = llm_service

    def run(
        self,
        query: str = "",
        document_text: str = "",
        title: str = "Research paper",
        session_id: str = "general",
        generate_audio: bool = True,
        overwrite_audio: bool = True,
        **_: Any,
    ) -> Dict[str, Any]:
        if not self.audio_service:
            raise ValueError("Audio service is not configured.")

        script = self.audio_service.build_podcast_script(
            title=title,
            summary=query or document_text[:5000],
            document_text=document_text,
            llm_service=self.llm,
        )
        audio_path = (
            self.audio_service.generate_audio(script, session_id=session_id, overwrite=overwrite_audio)
            if generate_audio
            else None
        )
        audio_url = f"/api/generated-audio/{session_id}.mp3" if audio_path else None

        response = "Generated a realistic spoken research explanation."
        if audio_url:
            response += " Audio was saved for playback and download."
        return {
            "selected_agent": self.name,
            "intent": "podcast_generation",
            "response": response,
            "sources": [],
            "artifacts": {"script": script, "audio_path": audio_path, "audio_url": audio_url},
        }
