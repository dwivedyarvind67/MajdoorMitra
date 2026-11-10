"""Run a non-persistent, real-credential smoke check of Gnani Timbre, Prisma, and Evon.

Usage: python smoke_gnani.py
The script speaks a synthetic Hindi sentence, transcribes that audio, and checks
that Evon returns a recognized wage intent. It never prints or stores the text,
credentials, or generated audio.
"""

import asyncio
import sys

from app.services.evon_service import ExtractionError, get_evon_service
from app.services.extraction_service import get_extraction_service
from app.services.prisma_service import ConfigurationError, TranscriptionError, get_prisma_service
from app.services.timbre_service import TTSError, get_timbre_service


async def main() -> int:
    stage = "Timbre"
    try:
        audio = await get_timbre_service().speak(
            "मैंने एक दिन काम किया और मेरी रोज़ की मज़दूरी पाँच सौ रुपये थी।",
            "hi",
        )
        if len(audio) < 44 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
            raise ValueError("Timbre did not return a WAV audio file.")
        print("PASS: Gnani Timbre returned WAV audio.")

        stage = "Prisma"
        transcript = await get_prisma_service().transcribe(
            audio,
            "hi",
            filename="synthetic-smoke.wav",
            content_type="audio/wav",
        )
        if not transcript.strip():
            raise ValueError("Prisma returned an empty transcript.")
        print("PASS: Gnani Prisma transcribed the synthetic audio.")

        stage = "Evon"
        raw = await get_evon_service().extract(transcript, "hi")
        validated = get_extraction_service().validate_and_fill(raw)
        if validated.intent != "log_work":
            raise ValueError("Evon did not identify the synthetic work statement.")
        print("PASS: Gnani Evon returned a validated work intent.")
        print(f"Unspecified required fields correctly marked: {len(validated.missing_fields)}.")
        return 0
    except (ConfigurationError, ExtractionError, TranscriptionError, TTSError, ValueError) as exc:
        # Provider service messages contain only safe setup/status details, never credentials or bodies.
        print(f"FAIL: Gnani {stage} smoke check: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Unknown exceptions may contain request data; report only the stage and type.
        print(f"FAIL: Gnani {stage} smoke check ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
