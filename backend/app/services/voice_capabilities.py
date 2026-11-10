"""Verified public capability registry for the Gnani speech APIs."""

from copy import deepcopy

from app.config import get_settings


LANGUAGES = [
    {"code": "bn-IN", "short_code": "bn", "name": "বাংলা", "english_name": "Bengali"},
    {"code": "en-IN", "short_code": "en", "name": "English", "english_name": "English"},
    {"code": "gu-IN", "short_code": "gu", "name": "ગુજરાતી", "english_name": "Gujarati"},
    {"code": "hi-IN", "short_code": "hi", "name": "हिन्दी", "english_name": "Hindi"},
    {"code": "kn-IN", "short_code": "kn", "name": "ಕನ್ನಡ", "english_name": "Kannada"},
    {"code": "ml-IN", "short_code": "ml", "name": "മലയാളം", "english_name": "Malayalam"},
    {"code": "mr-IN", "short_code": "mr", "name": "मराठी", "english_name": "Marathi"},
    {"code": "pa-IN", "short_code": "pa", "name": "ਪੰਜਾਬੀ", "english_name": "Punjabi"},
    {"code": "ta-IN", "short_code": "ta", "name": "தமிழ்", "english_name": "Tamil"},
    {"code": "te-IN", "short_code": "te", "name": "తెలుగు", "english_name": "Telugu"},
]

TAGS = [
    "<whispers>", "<laugh>", "<sigh>", "<excited>", "<pauses>", "<giggle>",
    "<coughs>", "<slow>", "<shouting>", "<exhales>", "<sniffles>", "<yawns>",
    "<clears throat>",
]

TIMBRE_V3_VOICES = [
    {"id": "Avinash", "gender": "male", "persona": "Professional", "description": "Professional, firm voice with deliberate pacing.", "languages": "all"},
    {"id": "Chetana", "gender": "female", "persona": "Warm and empathetic", "description": "Gentle, empathetic voice.", "languages": "all"},
    {"id": "Devansh", "gender": "male", "persona": "Conversational", "description": "Energetic, young conversational voice.", "languages": "all"},
    {"id": "Kalpana", "gender": "female", "persona": "Warm and empathetic", "description": "Empathetic, composed voice.", "languages": "all"},
    {"id": "Lakshmi", "gender": "female", "persona": "Expressive and energetic", "description": "Expressive, warm voice for storytelling.", "languages": "all"},
    {"id": "Prakash", "gender": "male", "persona": "Professional", "description": "Steady, deliberate voice.", "languages": "all"},
    {"id": "Riyaa", "gender": "female", "persona": "Confident and authoritative", "description": "Confident, lively voice.", "languages": "all"},
    {"id": "Shivani", "gender": "female", "persona": "Warm and empathetic", "description": "Warm, patient, empathy-first voice.", "languages": "all"},
    {"id": "Shubham", "gender": "male", "persona": "Expressive and energetic", "description": "Energetic, confident voice.", "languages": "all"},
    {"id": "Tarika", "gender": "female", "persona": "Warm and empathetic", "description": "Warm, reassuring voice.", "languages": "all"},
    {"id": "Vasudha", "gender": "female", "persona": "Expressive and energetic", "description": "Expressive, composed narration voice.", "languages": "all"},
    {"id": "Yashraj", "gender": "male", "persona": "Warm and empathetic", "description": "Warm narrative voice.", "languages": "all"},
    {"id": "Harshad", "gender": "male", "persona": "Professional", "description": "Professional, firm voice.", "languages": "all"},
]

# These two v2.5 voices are already exercised by the existing wage receipt flow.
TIMBRE_V25_VOICES = [
    {"id": "Nalini", "gender": "female", "persona": "Friendly", "description": "Hindi voice used by the existing receipt flow.", "languages": ["hi-IN"]},
    {"id": "Kaveri", "gender": "female", "persona": "Professional", "description": "English voice used by the existing receipt flow.", "languages": ["en-IN"]},
]


def get_capabilities() -> dict:
    """Return deep-copied registry data so callers cannot mutate module state."""
    settings = get_settings()
    local_mode = settings.GNANI_EVON_BACKEND.strip().lower() == "transformers"
    evon_languages = ["en-IN", "hi-IN", "bn-IN", "te-IN", "ta-IN", "mr-IN", "gu-IN", "kn-IN", "ml-IN", "or-IN", "pa-IN"]
    return {
        "languages": deepcopy(LANGUAGES),
        "prisma": {
            "model": "prisma-v3.0",
            "configured": bool(settings.GNANI_PRISMA_API_KEY.strip()),
            "account_verification": "previous_live_smoke_passed" if settings.GNANI_PRISMA_API_KEY.strip() else "not_configured",
            "languages": [item["code"] for item in LANGUAGES],
            "auto_detect": True,
            "code_switching": {"supported": True, "format": "codemix", "max_languages": 4},
        },
        "timbre": {
            "configured": bool(settings.GNANI_TIMBRE_API_KEY.strip()),
            "v3_account_verification": "previous_live_smoke_passed" if settings.GNANI_TIMBRE_API_KEY.strip() else "not_configured",
            "models": [
                {"id": "timbre-v2.5", "languages": [item["code"] for item in LANGUAGES], "voices": deepcopy(TIMBRE_V25_VOICES), "audio_tags": False},
                {"id": "timbre-v3.0", "languages": [item["code"] for item in LANGUAGES], "voices": deepcopy(TIMBRE_V3_VOICES), "audio_tags": True},
            ],
            "hinglish": {"language": "hi-en", "model": "timbre-v2.5", "voice": "Poorvi", "verified_account_access": False},
            "audio_tags": deepcopy(TAGS),
            "speed": {"min": 0.85, "max": 1.15, "default": 1.0},
        },
        "evon": {
            "backend": "transformers" if local_mode else "api",
            "model_id": settings.GNANI_EVON_MODEL_ID,
            "configured": True if local_mode else bool(settings.GNANI_EVON_API_KEY.strip()),
            "access": "runtime_requires_supported_host" if local_mode else "unverified",
            "reason": (
                "Evon v3.3 local Transformers is selected. It needs the optional Transformers 5.3+ runtime, Linux, and about 70 GB combined CUDA GPU memory; this runtime has not been loaded here."
                if local_mode
                else "The configured Evon API account previously returned HTTP 403. Structured extraction is unavailable until access is enabled; saved transcripts remain intact."
            ),
            "languages": evon_languages if local_mode else [],
        },
        "sources": [
            "https://docs.gnani.ai/api/STT/speech-to-text",
            "https://docs.gnani.ai/api/TTS/available-voices",
            "https://docs.gnani.ai/api/TTS/tts-inference",
        ],
    }

