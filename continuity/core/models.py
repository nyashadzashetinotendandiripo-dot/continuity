"""Core data models for Continuity."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MemoryType(str, Enum):
    EPISODIC = "episodic"    # What happened in conversations
    SEMANTIC = "semantic"    # Facts and knowledge
    PROCEDURAL = "procedural"  # How to do things


class Message(BaseModel):
    id: str = Field(default_factory=_uuid)
    role: Role
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    tokens: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    id: str = Field(default_factory=_uuid)
    provider: str
    model: str
    title: str | None = None
    summary: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    message_count: int = 0
    total_tokens: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Memory(BaseModel):
    id: str = Field(default_factory=_uuid)
    content: str
    memory_type: MemoryType
    confidence: float = 1.0
    source_conversation_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemporalFact(BaseModel):
    id: str = Field(default_factory=_uuid)
    subject: str
    predicate: str
    object: str
    valid_from: datetime = Field(default_factory=datetime.now)
    valid_to: datetime | None = None
    replaced_by: str | None = None
    confidence: float = 1.0
    source_conversation_id: str | None = None


class SessionInfo(BaseModel):
    """Returned when starting a new session."""
    session_id: str
    provider: str
    model: str
    title: str | None = None
    context_loaded: int = 0  # Number of memories loaded


class ContextResult(BaseModel):
    """Result of context retrieval."""
    relevant_memories: list[Memory]
    relevant_conversations: list[Conversation]
    recent_messages: list[Message]
    total_tokens_estimated: int
    query: str


class SessionDetail(BaseModel):
    """Full session history."""
    conversation: Conversation
    messages: list[Message]
    context: ContextResult | None = None


class SessionSummary(BaseModel):
    """Lightweight session info for listing."""
    id: str
    title: str | None
    provider: str
    model: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ProviderCapabilities(BaseModel):
    """What a provider supports."""
    supports_chat: bool = True
    supports_embeddings: bool = False
    supports_streaming: bool = True
    max_context_tokens: int = 128_000
    available_models: list[str] = Field(default_factory=list)


class ProviderConfig(BaseModel):
    """Configuration for a provider."""
    name: str
    api_key: str | None = None
    base_url: str | None = None
    default_model: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
