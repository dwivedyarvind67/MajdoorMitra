"""Gnani Prisma speech-to-text client."""

import httpx

from app.config import get_settings


class ConfigurationError(Exception):
    """Raised when a required provider setting is absent."""


class TranscriptionError(Exception):
    """Raised when Prisma fails to return a transcript."""


class PrismaService:
    LANGUAGE_CODES = {
        "bn": "bn-IN", "en": "en-IN", "gu": "gu-IN", "hi": "hi-IN",
        "kn": "kn-IN", "ml": "ml-IN", "mr": "mr-IN", "pa": "pa-IN",
        "ta": "ta-IN", "te": "te-IN",
    }
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.GNANI_PRISMA_API_KEY
        self.api_url = settings.GNANI_PRISMA_API_URL

    def _check_config(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise ConfigurationError("Gnani Prisma is not configured. Add GNANI_PRISMA_API_KEY to backend/.env.")
        if not self.api_url or not self.api_url.strip():
            raise ConfigurationError("Gnani Prisma API URL is not configured.")

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hi",
        filename: str = "recording.wav",
        content_type: str = "audio/wav",
    ) -> str:
        self._check_config()
        if not audio_data:
            raise TranscriptionError("The audio recording is empty.")

        normalized_language = language.strip().lower()
        is_hinglish = normalized_language == "hinglish"
        lang_code = (
            "hi-IN,en-IN" if is_hinglish
            else "indic-auto" if normalized_language == "auto"
            else self.LANGUAGE_CODES.get(normalized_language, normalized_language)
        )
        headers = {"X-API-Key-ID": self.api_key.strip()}
        files = {"audio_file": (filename, audio_data, content_type)}
        data = {
            "model": "prisma-v3.0",
            "language_code": lang_code,
            "format": "codemix" if is_hinglish else "transcribe",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.api_url, headers=headers, files=files, data=data)
            if response.status_code != 200:
                raise TranscriptionError(f"Gnani Prisma returned HTTP {response.status_code}.")
            result = response.json()
            transcript = ""
            if isinstance(result, dict):
                nested = result.get("data")
                transcript = (
                    result.get("transcript")
                    or result.get("text")
                    or (nested.get("transcript") if isinstance(nested, dict) else "")
                    or ""
                )
            elif isinstance(result, list) and result and isinstance(result[0], dict):
                transcript = result[0].get("transcript") or result[0].get("text") or ""
            transcript = str(transcript).strip()
            if not transcript:
                raise TranscriptionError("Gnani Prisma returned an empty transcript.")
            return transcript
        except httpx.TimeoutException as exc:
            raise TranscriptionError("Gnani Prisma timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise TranscriptionError("Gnani Prisma could not be reached. Please try again.") from exc


def get_prisma_service() -> PrismaService:
    return PrismaService()
