"""Google Gemini provider."""

from __future__ import annotations

from typing import AsyncIterator

import httpx

from continuity.core.models import Message, ProviderCapabilities, Role
from continuity.providers.base import AIProvider


class GoogleProvider(AIProvider):
    name = "google"

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: object,
    ) -> Message:
        model = model or self.default_model()
        contents = []
        for m in messages:
            role = "model" if m.role == Role.ASSISTANT else "user"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent?key={self.config.api_key}"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return Message(
            role=Role.ASSISTANT,
            content=text,
            tokens=usage.get("totalTokenCount"),
            metadata={"model": model},
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
        contents = []
        for m in messages:
            role = "model" if m.role == Role.ASSISTANT else "user"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:streamGenerateContent?alt=sse&key={self.config.api_key}"
        )
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, timeout=120) as resp:
                resp.raise_for_status()
                import json
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = json.loads(line[6:])
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            yield parts[0].get("text", "")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_chat=True,
            supports_embeddings=False,
            supports_streaming=True,
            max_context_tokens=1_000_000,
            available_models=[
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
            ],
        )
