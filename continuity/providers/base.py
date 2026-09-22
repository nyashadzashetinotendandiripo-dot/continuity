"""Abstract provider interface for AI models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from continuity.core.models import Message, ProviderCapabilities, ProviderConfig


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: object,
    ) -> Message:
        """Send messages and get a response."""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: object,
    ) -> AsyncIterator[str]:
        """Stream response tokens."""
        yield ""  # pragma: no cover

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    def default_model(self) -> str:
        """Default model for this provider."""
        return self.config.default_model or self.capabilities().available_models[0]
