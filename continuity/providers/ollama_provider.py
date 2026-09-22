"""Ollama provider (local models)."""

from __future__ import annotations

from typing import AsyncIterator

import httpx

from continuity.core.models import Message, ProviderCapabilities, Role
from continuity.providers.base import AIProvider


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, config: "ProviderConfig") -> None:
        super().__init__(config)
        self._base_url = (config.base_url or "http://localhost:11434").rstrip("/")

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: object,
    ) -> Message:
        model = model or self.default_model()
        payload = {
            "model": model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()
        return Message(
            role=Role.ASSISTANT,
            content=data["message"]["content"],
            tokens=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            metadata={"model": model, "total_duration_ns": data.get("total_duration")},
        )

    async def chat_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: object,
    ) -> AsyncIterator[str]:
        model = model or self.default_model()
        payload = {
            "model": model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=300,
            ) as resp:
                resp.raise_for_status()
                import json
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if "message" in chunk:
                        yield chunk["message"].get("content", "")

    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_chat=True,
            supports_embeddings=True,
            supports_streaming=True,
            max_context_tokens=32_768,
            available_models=[],  # Dynamic, fetched from server
        )
