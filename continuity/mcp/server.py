"""MCP server for Continuity — works with Claude Desktop, Cursor, Windsurf, Zed, etc."""

from __future__ import annotations

from continuity.core.memory import MemoryEngine
from continuity.core.models import MemoryType, Role
from continuity.storage.sqlite import Storage

try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError("FastMCP not installed. Run: pip install fastmcp")

mcp = FastMCP(
    "continuity",
    description="AI conversation memory — never lose the thread. Works with any AI provider.",
)

_engine: MemoryEngine | None = None


def _get_engine() -> MemoryEngine:
    global _engine
    if _engine is None:
        _engine = MemoryEngine()
    return _engine


# ── TOOLS ─────────────────────────────────────────────────────────


@mcp.tool()
async def start_session(
    provider: str = "openai",
    model: str = "gpt-4o",
    title: str | None = None,
) -> dict:
    """Start a new conversation session with memory context.

    Args:
        provider: AI provider (openai, anthropic, google, xai, ollama, openai-compatible)
        model: Model name (gpt-4o, claude-3-5-sonnet, gemini-2.0-flash, llama3, etc.)
        title: Optional title for the session

    Returns:
        Session info with ID and context loaded.
    """
    engine = _get_engine()
    conv = engine.start_session(provider, model, title)
    context = engine.get_context([])
    return {
        "session_id": conv.id,
        "provider": provider,
        "model": model,
        "title": title,
        "context_loaded": len(context.relevant_memories),
        "message": f"Session started. Use session_id '{conv.id[:8]}' to continue.",
    }


@mcp.tool()
async def get_context(
    session_id: str = "",
    query: str = "",
    max_tokens: int = 2000,
) -> dict:
    """Get relevant context for current conversation. Use this before responding to remember past context.

    Args:
        session_id: Current session ID (optional, searches all if empty)
        query: What to search for in memory (optional, uses recent context if empty)
        max_tokens: Maximum tokens for context budget

    Returns:
        Relevant memories, recent conversations, and messages.
    """
    engine = _get_engine()
    messages = engine.storage.get_messages(session_id) if session_id else []
    context = engine.get_context(messages, query=query or None, max_tokens=max_tokens)
    
    # Build a ready-to-use system prompt
    system_prompt = engine.build_system_prompt(context)
    
    return {
        "memories": [
            {"content": m.content, "type": m.memory_type.value, "confidence": m.confidence}
            for m in context.relevant_memories
        ],
        "recent_conversations": [
            {"title": c.title, "provider": c.provider, "model": c.model, "messages": c.message_count}
            for c in context.relevant_conversations
        ],
        "recent_messages": [
            {"role": m.role.value, "content": m.content[:300]}
            for m in context.recent_messages[-10:]
        ],
        "system_prompt": system_prompt,
        "total_tokens_estimated": context.total_tokens_estimated,
    }


@mcp.tool()
async def store_memory(
    content: str,
    memory_type: str = "semantic",
    confidence: float = 1.0,
    source_session_id: str | None = None,
) -> dict:
    """Store important information for future recall. Use this after important decisions, facts, or user preferences.

    Args:
        content: The information to remember (be specific and clear)
        memory_type: episodic (what happened), semantic (facts), procedural (how to do things)
        confidence: Confidence level (0.0 to 1.0)
        source_session_id: Optional session this came from

    Returns:
        Stored memory info.
    """
    engine = _get_engine()
    mt = MemoryType(memory_type)
    mem = engine.store_memory(
        content,
        memory_type=mt,
        confidence=confidence,
        source_conversation_id=source_session_id,
    )
    return {
        "id": mem.id,
        "content": mem.content,
        "type": mem.memory_type.value,
        "confidence": mem.confidence,
        "message": f"Memory stored successfully.",
    }


@mcp.tool()
async def search_memory(
    query: str,
    limit: int = 10,
    memory_type: str | None = None,
) -> list[dict]:
    """Search stored memories by semantic similarity. Use this to find relevant past context.

    Args:
        query: What to search for (natural language)
        limit: Maximum results (default 10)
        memory_type: Optional filter (episodic, semantic, procedural)

    Returns:
        List of matching memories with relevance scores.
    """
    engine = _get_engine()
    mt = MemoryType(memory_type) if memory_type else None
    results = engine.search_memories(query, limit=limit, memory_type=mt)
    return [
        {
            "id": m.id,
            "content": m.content,
            "type": m.memory_type.value,
            "confidence": m.confidence,
            "relevance_score": round(score, 4),
        }
        for m, score in results
    ]


@mcp.tool()
async def list_sessions(
    limit: int = 20,
    provider: str | None = None,
) -> list[dict]:
    """List conversation sessions.

    Args:
        limit: Maximum sessions to return
        provider: Optional filter by provider name

    Returns:
        List of session summaries.
    """
    engine = _get_engine()
    convs = engine.storage.list_conversations(limit=limit)
    if provider:
        convs = [c for c in convs if c.provider == provider]
    return [
        {
            "id": c.id,
            "title": c.title,
            "provider": c.provider,
            "model": c.model,
            "message_count": c.message_count,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in convs
    ]


@mcp.tool()
async def add_message(
    session_id: str,
    role: str,
    content: str,
) -> dict:
    """Add a message to a conversation session.

    Args:
        session_id: Session to add to
        role: Message role (user, assistant, system)
        content: Message content

    Returns:
        Stored message info.
    """
    engine = _get_engine()
    msg = engine.add_message(session_id, Role(role), content)
    return {
        "id": msg.id,
        "role": msg.role.value,
        "content": msg.content[:200],
        "created_at": msg.created_at.isoformat(),
        "message": "Message added to session.",
    }


@mcp.tool()
async def build_prompt(
    session_id: str,
    base_prompt: str = "",
) -> str:
    """Build a system prompt with relevant memory context. Use this before responding.

    Args:
        session_id: Current session ID
        base_prompt: Base system prompt to enhance (optional)

    Returns:
        Enhanced system prompt with memory context.
    """
    engine = _get_engine()
    messages = engine.storage.get_messages(session_id)
    context = engine.get_context(messages)
    return engine.build_system_prompt(context, base_prompt=base_prompt)


@mcp.tool()
async def get_stats() -> dict:
    """Get storage statistics.

    Returns:
        Statistics about stored data.
    """
    engine = _get_engine()
    stats = engine.storage.get_stats()
    stats["db_size_mb"] = round(stats["db_size_bytes"] / (1024 * 1024), 2)
    return stats


@mcp.tool()
async def export_memories() -> dict:
    """Export all memories for backup or transfer.

    Returns:
        All memories and session info.
    """
    engine = _get_engine()
    return {
        "memories": [
            {"content": m.content, "type": m.memory_type.value, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in engine.storage.list_memories(limit=10000)
        ],
        "stats": engine.storage.get_stats(),
    }


# ── RESOURCES ─────────────────────────────────────────────────────


@mcp.resource("continuity://stats")
async def resource_stats() -> dict:
    """Current storage statistics."""
    engine = _get_engine()
    return engine.storage.get_stats()


@mcp.resource("continuity://config")
async def resource_config() -> dict:
    """Current configuration and available providers."""
    return {
        "storage": "local SQLite",
        "embeddings": "sentence-transformers (all-MiniLM-L6-v2)",
        "providers": {
            "openai": "GPT-4, GPT-4o, o1",
            "anthropic": "Claude 3.5, Claude 3",
            "google": "Gemini 1.5, 2.0",
            "xai": "Grok",
            "ollama": "Any local model",
            "openai-compatible": "Any OpenAI-compatible API",
        },
    }


# ── MAIN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
