"""Memory engine — extraction, retrieval, and context injection."""

from __future__ import annotations

from datetime import datetime

from continuity.core.embeddings import EmbeddingService
from continuity.core.models import (
    Conversation,
    ContextResult,
    Memory,
    MemoryType,
    Message,
    Role,
)
from continuity.storage.sqlite import Storage


class MemoryEngine:
    """Core engine for managing conversation memory."""

    def __init__(self, storage: Storage | None = None) -> None:
        self.storage = storage or Storage()
        self.embeddings = EmbeddingService()

    def start_session(
        self,
        provider: str,
        model: str,
        title: str | None = None,
    ) -> Conversation:
        """Create a new conversation session."""
        conv = Conversation(provider=provider, model=model, title=title)
        self.storage.save_conversation(conv)
        return conv

    def add_message(
        self,
        conversation_id: str,
        role: Role,
        content: str,
        **kwargs: object,
    ) -> Message:
        """Add a message to a conversation."""
        msg = Message(role=role, content=content, **kwargs)
        self.storage.save_message(conversation_id, msg)
        return msg

    def store_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        confidence: float = 1.0,
        source_conversation_id: str | None = None,
    ) -> Memory:
        """Store a memory and generate its embedding."""
        memory = Memory(
            content=content,
            memory_type=memory_type,
            confidence=confidence,
            source_conversation_id=source_conversation_id,
        )
        self.storage.save_memory(memory)
        # Generate embedding in background (simplified: do it inline)
        embedding = self.embeddings.embed_one(content)
        self.storage.update_memory_embedding(memory.id, embedding)
        return memory

    def search_memories(
        self,
        query: str,
        limit: int = 10,
        memory_type: MemoryType | None = None,
    ) -> list[tuple[Memory, float]]:
        """Search memories by semantic similarity."""
        query_embedding = self.embeddings.embed_one(query)
        return self.storage.search_memories_by_embedding(
            query_embedding, limit=limit, memory_type=memory_type
        )

    def get_context(
        self,
        current_messages: list[Message],
        query: str | None = None,
        max_tokens: int = 2000,
    ) -> ContextResult:
        """Get relevant context for the current conversation.

        This is the core of what makes Continuity work — it pulls together:
        1. Relevant memories from past conversations
        2. Recent messages from this session
        3. Related past conversations
        """
        # Build query from recent messages if not provided
        if query is None:
            recent_content = " ".join(m.content for m in current_messages[-5:])
            query = recent_content[:500] if recent_content else ""

        # Search relevant memories
        relevant_memories: list[Memory] = []
        if query:
            results = self.search_memories(query, limit=10)
            relevant_memories = [m for m, _ in results]

        # Get recent messages across all sessions
        recent_messages = self.storage.get_recent_messages(limit=20)

        # Get recent conversations for context
        recent_conversations = self.storage.list_conversations(limit=5)

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        total_chars = sum(len(m.content) for m in relevant_memories)
        total_chars += sum(len(m.content) for m in recent_messages)
        total_tokens_estimated = total_chars // 4

        # Trim to budget
        while total_tokens_estimated > max_tokens and relevant_memories:
            removed = relevant_memories.pop()
            total_tokens_estimated -= len(removed.content) // 4

        return ContextResult(
            relevant_memories=relevant_memories,
            relevant_conversations=recent_conversations,
            recent_messages=recent_messages,
            total_tokens_estimated=total_tokens_estimated,
            query=query,
        )

    def build_system_prompt(
        self,
        context: ContextResult,
        base_prompt: str = "",
    ) -> str:
        """Build a system prompt that includes relevant context.

        This is where the magic happens — the AI gets loaded with
        relevant context from past conversations, making it feel
        like it remembers everything.
        """
        parts = []

        if base_prompt:
            parts.append(base_prompt)

        if context.relevant_memories:
            parts.append("## Relevant memories from past conversations:")
            for mem in context.relevant_memories[:5]:
                parts.append(f"- {mem.content}")

        if context.relevant_conversations:
            parts.append("\n## Recent conversation topics:")
            for conv in context.relevant_conversations[:3]:
                title = conv.title or "Untitled"
                parts.append(f"- {title} ({conv.provider}/{conv.model}, {conv.message_count} messages)")

        if context.recent_messages:
            parts.append("\n## Recent messages in this conversation:")
            for msg in context.recent_messages[-5:]:
                parts.append(f"[{msg.role.value}]: {msg.content[:200]}")

        parts.append("\n## Instructions:")
        parts.append("You have access to memory from past conversations. Use this context naturally.")
        parts.append("If the user refers to something from a past conversation, you may remember it.")
        parts.append("Do not explicitly mention that you have memory unless asked.")

        return "\n".join(parts)

    def consolidate_memories(self) -> int:
        """Find and merge duplicate memories. Returns count of merges."""
        all_memories = self.storage.list_memories(limit=1000)
        merged = 0

        # Simple deduplication: find memories with very similar embeddings
        seen_embeddings: dict[str, list[str]] = {}
        for mem in all_memories:
            # Use first 8 chars of content as rough key
            key = mem.content[:8].lower().strip()
            if key in seen_embeddings:
                # Potential duplicate — keep the one with higher confidence
                existing_id = seen_embeddings[key][0]
                existing = self.storage.get_memory(existing_id)
                if existing and mem.confidence > existing.confidence:
                    self.storage.delete_memory(existing_id)
                    seen_embeddings[key].pop(0)
                else:
                    self.storage.delete_memory(mem.id)
                    merged += 1
            else:
                seen_embeddings[key] = [mem.id]

        return merged
