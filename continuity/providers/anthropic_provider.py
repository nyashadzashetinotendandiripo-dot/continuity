"""Anthropic provider (Claude)."""

from __future__ import annotations

from typing import AsyncIterator

import httpx

from continuity.core.models import Message, ProviderCapabilities, Role
from continuity.providers.base import AIProvider


class AnthropicProvider(AIProvider):
    name = "anthropic"

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: object,
    ) -> Message:
        model = model or self.default_model()
        # Anthropic uses system message separately
        system_msg = ""
        chat_messages = []
        for m in messages:
            if m.role == Role.SYSTEM:
                system_msg = m.content
            else:
                chat_messages.append({"role": m.role.value, "content": m.content})

        payload: dict = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers={
                    "x-api-key": self.config.api_key or "",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
        content = data["content"][0]["text"]
        return Message(
            role=Role.ASSISTANT,
            content=content,
            tokens=data.get("usage", {}).get("input_tokens", 0)
            + data.get("usage", {}).get("output_tokens", 0),
            metadata={"model": model, "stop_reason": data.get("stop_reason")},
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
        system_msg = ""
        chat_messages = []
        for m in messages:
            if m.role == Role.SYSTEM:
                system_msg = m.content
            else:
                chat_messages.append({"role": m.role.value, "content": m.content})

        payload: dict = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers={
                    "x-api-key": self.config.api_key or "",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                import json
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = json.loads(line[6:])
                    if data.get("type") == "content_block_delta":
                        yield data.get("delta", {}).get("text", "")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_chat=True,
            supports_embeddings=False,
            supports_streaming=True,
            max_context_tokens=200_000,
            available_models=[
                "claude-sonnet-4-20250514",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
                "claude-3-haiku-20240307",
            ],
        )
