"""Gnani Timbre text-to-speech client."""

import httpx

from app.config import get_settings
from app.services.prisma_service import ConfigurationError


class TTSError(Exception):
    """Raised when Timbre fails to return playable audio."""


class TimbreService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.GNANI_TIMBRE_API_KEY
        self.api_url = settings.GNANI_TIMBRE_API_URL

    def _check_config(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise ConfigurationError("Gnani Timbre is not configured. Add GNANI_TIMBRE_API_KEY to backend/.env.")
        if not self.api_url or not self.api_url.strip():
            raise ConfigurationError("Gnani Timbre API URL is not configured.")

    async def speak(
        self,
        text: str,
        language: str = "hi",
        model: str = "timbre-v2.5",
        voice: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        self._check_config()
        if not text.strip():
            raise TTSError("There is no text to speak.")

        aliases = {"hi": "hi-IN", "en": "en-IN"}
        lang_code = aliases.get(language, language)
        voice_name = voice or ("Nalini" if lang_code == "hi-IN" else "Kaveri")
        headers = {
            "X-API-Key-ID": self.api_key.strip(),
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "voice": voice_name,
            "model": model,
            "language": lang_code,
            "speed": speed,
            "audio_config": {
                "encoding": "linear_pcm",
                "container": "wav",
                "sample_rate": 24000,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise TTSError(f"Gnani Timbre returned HTTP {response.status_code}.")
            if not response.content:
                raise TTSError("Gnani Timbre returned empty audio.")
            return response.content
        except httpx.TimeoutException as exc:
            raise TTSError("Gnani Timbre timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise TTSError("Gnani Timbre could not be reached. Please try again.") from exc


def get_timbre_service() -> TimbreService:
    return TimbreService()
