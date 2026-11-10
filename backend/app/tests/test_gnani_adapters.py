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

