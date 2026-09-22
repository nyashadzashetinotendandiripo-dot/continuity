"""Provider registry — auto-discovery and management."""

from __future__ import annotations

from continuity.core.models import ProviderConfig
from continuity.providers.base import AIProvider


_REGISTRY: dict[str, type[AIProvider]] = {}


def register_provider(name: str, cls: type[AIProvider]) -> None:
    _REGISTRY[name] = cls


def get_provider_class(name: str) -> type[AIProvider] | None:
    return _REGISTRY.get(name)


def list_providers() -> list[str]:
    return list(_REGISTRY.keys())


def create_provider(config: ProviderConfig) -> AIProvider:
    cls = _REGISTRY.get(config.name)
    if cls is None:
        raise ValueError(
            f"Unknown provider: {config.name}. "
            f"Available: {', '.join(_REGISTRY.keys())}"
        )
    return cls(config)


def _register_all() -> None:
    from continuity.providers.openai_provider import OpenAIProvider
    from continuity.providers.anthropic_provider import AnthropicProvider
    from continuity.providers.google_provider import GoogleProvider
    from continuity.providers.xai_provider import XAIProvider
    from continuity.providers.ollama_provider import OllamaProvider
    from continuity.providers.openai_compat_provider import OpenAICompatibleProvider

    register_provider("openai", OpenAIProvider)
    register_provider("anthropic", AnthropicProvider)
    register_provider("google", GoogleProvider)
    register_provider("xai", XAIProvider)
    register_provider("ollama", OllamaProvider)
    register_provider("openai-compatible", OpenAICompatibleProvider)


_register_all()
