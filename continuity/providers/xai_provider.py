"""xAI (Grok) provider."""

from __future__ import annotations

from typing import AsyncIterator

import httpx

from continuity.core.models import Message, ProviderCapabilities, Role
from continuity.providers.base import AIProvider


class XAIProvider(AIProvider):
    name = "xai"

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
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
        choice = data["choices"][0]
        return Message(
            role=Role.ASSISTANT,
            content=choice["message"]["content"],
            tokens=data.get("usage", {}).get("total_tokens"),
            metadata={"model": model, "finish_reason": choice.get("finish_reason")},
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
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://api.x.ai/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                import json
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_chat=True,
            supports_embeddings=False,
            supports_streaming=True,
            max_context_tokens=131_072,
            available_models=[
                "grok-2",
                "grok-2-mini",
                "grok-3",
                "grok-3-mini",
            ],
        )
