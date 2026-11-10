"""Contract-level tests for the three Gnani adapters using safe HTTP mocks."""

import pytest

from app.services.evon_service import EvonService
from app.services.prisma_service import PrismaService
from app.services.timbre_service import TimbreService


class MockResponse:
    def __init__(self, status_code=200, *, body=None, content=b""):
        self.status_code = status_code
        self._body = body or {}
        self.content = content

    def json(self):
        return self._body


class MockClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def configured(monkeypatch, service_class, url):
    service = service_class()
    service.api_key = "test-api-key"
    service.api_url = url
    return service


@pytest.mark.asyncio
async def test_prisma_uses_documented_rest_multipart_contract(monkeypatch):
    response = MockResponse(body={"success": True, "transcript": "दो दिन काम किया"})
    client = MockClient(response)
    monkeypatch.setattr("app.services.prisma_service.httpx.AsyncClient", lambda **_kwargs: client)
    service = configured(monkeypatch, PrismaService, "https://api.vachana.ai/stt/v3")

    transcript = await service.transcribe(
        b"audio", "hi", filename="worker.wav", content_type="audio/wav"
    )

    args, kwargs = client.calls[0]
    assert args == ("https://api.vachana.ai/stt/v3",)
    assert kwargs["headers"] == {"X-API-Key-ID": "test-api-key"}
    assert kwargs["data"] == {
        "model": "prisma-v3.0",
        "language_code": "hi-IN",
        "format": "transcribe",
    }
    assert kwargs["files"]["audio_file"] == ("worker.wav", b"audio", "audio/wav")
    assert transcript == "दो दिन काम किया"


@pytest.mark.asyncio
async def test_prisma_hinglish_uses_documented_v3_codemix_format(monkeypatch):
    client = MockClient(MockResponse(body={"transcript": "Kal 2 din kaam kiya"}))
    monkeypatch.setattr("app.services.prisma_service.httpx.AsyncClient", lambda **_kwargs: client)
    service = configured(monkeypatch, PrismaService, "https://api.vachana.ai/stt/v3")

    await service.transcribe(b"audio", "hinglish")

    assert client.calls[0][1]["data"] == {
        "model": "prisma-v3.0",
        "language_code": "hi-IN,en-IN",
        "format": "codemix",
    }


@pytest.mark.asyncio
async def test_prisma_maps_all_verified_indic_locales(monkeypatch):
    client = MockClient(MockResponse(body={"transcript": "நான் வேலை செய்தேன்"}))
    monkeypatch.setattr("app.services.prisma_service.httpx.AsyncClient", lambda **_kwargs: client)
    service = configured(monkeypatch, PrismaService, "https://api.vachana.ai/stt/v3")

    await service.transcribe(b"audio", "ta")

    assert client.calls[0][1]["data"]["language_code"] == "ta-IN"


@pytest.mark.asyncio
async def test_timbre_uses_documented_rest_contract_and_english_voice(monkeypatch):
    response = MockResponse(content=b"RIFF\x00\x00\x00\x00WAVEaudio")
    client = MockClient(response)
    monkeypatch.setattr("app.services.timbre_service.httpx.AsyncClient", lambda **_kwargs: client)
    service = configured(
        monkeypatch, TimbreService, "https://api.vachana.ai/api/v1/tts/inference"
    )

    audio = await service.speak("Your wage statement is ready.", "en")

    args, kwargs = client.calls[0]
    assert args == ("https://api.vachana.ai/api/v1/tts/inference",)
    assert kwargs["headers"]["X-API-Key-ID"] == "test-api-key"
    assert kwargs["json"]["model"] == "timbre-v2.5"
    assert kwargs["json"]["voice"] == "Kaveri"
    assert kwargs["json"]["language"] == "en-IN"
    assert audio.startswith(b"RIFF")


@pytest.mark.asyncio
async def test_timbre_accepts_verified_v3_voice_language_and_speed(monkeypatch):
    response = MockResponse(content=b"RIFF\x00\x00\x00\x00WAVEaudio")
    client = MockClient(response)
    monkeypatch.setattr("app.services.timbre_service.httpx.AsyncClient", lambda **_kwargs: client)
    service = configured(monkeypatch, TimbreService, "https://api.vachana.ai/api/v1/tts/inference")

    await service.speak("नमस्ते", language="hi-IN", model="timbre-v3.0", voice="Shivani", speed=0.9)

    payload = client.calls[0][1]["json"]
    assert payload["model"] == "timbre-v3.0"
    assert payload["voice"] == "Shivani"
    assert payload["language"] == "hi-IN"
    assert payload["speed"] == 0.9


@pytest.mark.asyncio
async def test_evon_extracts_json_from_chat_completion_shape(monkeypatch):
    response = MockResponse(
        body={"choices": [{"message": {"content": '{"intent":"log_work","days_worked":2}'}}]}
    )
    client = MockClient(response)
    monkeypatch.setattr("app.services.evon_service.httpx.AsyncClient", lambda **_kwargs: client)
    service = configured(monkeypatch, EvonService, "https://api.vachana.ai/v1/chat/completions")

    result = await service.extract("दो दिन काम किया", "hi")

    args, kwargs = client.calls[0]
    assert args == ("https://api.vachana.ai/v1/chat/completions",)
    assert kwargs["headers"]["X-API-Key-ID"] == "test-api-key"
    assert kwargs["json"]["response_format"] == {"type": "json_object"}
    assert result == {"intent": "log_work", "days_worked": 2}


@pytest.mark.asyncio
async def test_evon_http_403_is_a_real_provider_failure_not_a_fallback(monkeypatch):
    from app.services.evon_service import ExtractionError

    client = MockClient(MockResponse(status_code=403))
    monkeypatch.setattr("app.services.evon_service.httpx.AsyncClient", lambda **_kwargs: client)
    service = configured(monkeypatch, EvonService, "https://api.vachana.ai/v1/chat/completions")

    with pytest.raises(ExtractionError, match="HTTP 403"):
        await service.extract("दो दिन काम किया", "hi")


@pytest.mark.asyncio
async def test_evon_transformers_backend_uses_local_generation_without_api_call(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "GNANI_EVON_BACKEND", "transformers")
    monkeypatch.setattr(settings, "GNANI_EVON_MODEL_ID", "gnani/gnani-evon-v3.3-30B-A3B")
    monkeypatch.setattr(
        "app.services.evon_service._generate_with_transformers",
        lambda messages, model_id: '{"intent":"log_work","days_worked":2}',
    )
    service = EvonService()

    result = await service.extract("दो दिन काम किया", "hi")

    assert result == {"intent": "log_work", "days_worked": 2}


def test_evon_transformers_backend_rejects_unsupported_windows_host_cleanly(monkeypatch):
    from app.services.evon_service import _generate_with_transformers
    from app.services.prisma_service import ConfigurationError

    monkeypatch.setattr("app.services.evon_service.platform.system", lambda: "Windows")
    with pytest.raises(ConfigurationError, match="supported on Linux"):
        _generate_with_transformers([], "gnani/gnani-evon-v3.3-30B-A3B")

