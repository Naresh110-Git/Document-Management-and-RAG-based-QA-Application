from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from time import perf_counter
from typing import AsyncIterator

import httpx

try:
    import openai
except Exception:
    openai = None

from app.core.config import Settings


class LLMError(Exception):
    pass


class BaseProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        raise NotImplementedError()

    async def stream_generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> AsyncIterator[str]:
        text = await self.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        for idx in range(0, len(text), 64):
            yield text[idx : idx + 64]
            await asyncio.sleep(0)


class OllamaProvider(BaseProvider):
    async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        base_url = self.settings.ollama_base_url.rstrip("/")
        url = f"{base_url}/api/generate"
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                r = await client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    alt_url = f"{base_url}/api/rest/v1/generate"
                    r = await client.post(alt_url, json={"model": self.settings.ollama_model, "prompt": prompt, "max_tokens": max_tokens, "temperature": temperature})
                    r.raise_for_status()
                    data = r.json()
                else:
                    raise

        if isinstance(data, dict):
            if "response" in data:
                return str(data["response"])
            results = data.get("results") or []
            if results:
                first = results[0]
                content = first.get("content") or []
                if content:
                    text = content[0].get("text") if isinstance(content[0], dict) else content[0]
                    return str(text or "")
        raise LLMError("empty or invalid response from Ollama")


class OpenAIProvider(BaseProvider):
    async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        if openai is None or not self.settings.openai_api_key:
            raise LLMError("OpenAI client unavailable or API key not set")

        def sync_call() -> str:
            if hasattr(openai, "OpenAI") and callable(getattr(openai, "OpenAI")):
                try:
                    client = openai.OpenAI(api_key=self.settings.openai_api_key)
                    response = client.chat.completions.create(
                        model=self.settings.openai_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    return response.choices[0].message.content or ""
                except Exception:
                    if not hasattr(openai, "ChatCompletion"):
                        raise

            if hasattr(openai, "ChatCompletion"):
                response = openai.ChatCompletion.create(
                    model=self.settings.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                choices = response.get("choices") if isinstance(response, dict) else getattr(response, "choices", [])
                if not choices:
                    raise LLMError("empty choices from OpenAI")
                first = choices[0]
                if isinstance(first, dict):
                    return first.get("message", {}).get("content", "")
                return getattr(first, "message", {}).content or ""

            raise LLMError("No supported OpenAI API method found")

        return await asyncio.to_thread(sync_call)


class HuggingFaceProvider(BaseProvider):
    async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        if not self.settings.huggingface_api_key:
            raise LLMError("HuggingFace API key not set")

        url = f"https://api-inference.huggingface.co/models/{self.settings.huggingface_model}"
        headers = {"Authorization": f"Bearer {self.settings.huggingface_api_key}"}
        payload = {
            "inputs": prompt,
            "options": {"use_cache": False},
            "parameters": {"max_new_tokens": max_tokens, "temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        if isinstance(data, dict) and "error" in data:
            raise LLMError("huggingface error: " + str(data.get("error")))
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                return str(first.get("generated_text", ""))
            return str(first)
        raise LLMError("unexpected HuggingFace response shape")


@dataclass
class LLMService:
    settings: Settings

    def __post_init__(self) -> None:
        self.provider = self._build_provider()

    def _build_provider(self) -> BaseProvider:
        p = self.settings.llm_provider
        if p == "ollama":
            return OllamaProvider(self.settings)
        if p == "openai":
            return OpenAIProvider(self.settings)
        if p == "huggingface":
            return HuggingFaceProvider(self.settings)
        return OllamaProvider(self.settings)

    async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        start = perf_counter()
        try:
            text = await self.provider.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        except Exception as exc:
            raise LLMError(str(exc)) from exc
        finally:
            _ = perf_counter() - start
        return text

    async def stream_generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> AsyncIterator[str]:
        async for chunk in self.provider.stream_generate(prompt, max_tokens=max_tokens, temperature=temperature):
            yield chunk
