import types
import pytest

from app.core.config import Settings


@pytest.mark.asyncio
async def test_ollama_provider_success(monkeypatch):
    from app.services import llm as llm_mod

    # Fake AsyncClient and response
    class FakeResponse:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None):
            return FakeResponse({"results": [{"content": [{"text": "Ollama answer"}]}]})

    monkeypatch.setattr(llm_mod, "httpx", types.SimpleNamespace(AsyncClient=FakeAsyncClient))

    settings = Settings()
    settings.llm_provider = "ollama"
    service = llm_mod.LLMService(settings)

    out = await service.generate("hello")
    assert out == "Ollama answer"


@pytest.mark.asyncio
async def test_openai_provider_success(monkeypatch):
    import app.services.llm as llm_mod

    # Inject a fake openai module with ChatCompletion.create
    class ChatCompletion:
        @staticmethod
        def create(*args, **kwargs):
            return {"choices": [{"message": {"content": "OpenAI answer"}}]}

    fake_openai = types.SimpleNamespace(ChatCompletion=ChatCompletion)
    monkeypatch.setattr(llm_mod, "openai", fake_openai)

    settings = Settings()
    settings.llm_provider = "openai"
    settings.openai_api_key = "fake"
    settings.openai_model = "test-model"

    service = llm_mod.LLMService(settings)
    out = await service.generate("hello")
    assert out == "OpenAI answer"


@pytest.mark.asyncio
async def test_huggingface_provider_success(monkeypatch):
    from app.services import llm as llm_mod

    class FakeResponse:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None):
            return FakeResponse([{"generated_text": "HF answer"}])

    monkeypatch.setattr(llm_mod, "httpx", types.SimpleNamespace(AsyncClient=FakeAsyncClient))

    settings = Settings()
    settings.llm_provider = "huggingface"
    settings.huggingface_api_key = "fake"
    settings.huggingface_model = "some/model"

    service = llm_mod.LLMService(settings)
    out = await service.generate("hello")
    assert "HF answer" in out
