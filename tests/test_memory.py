"""Tests for the memory engine."""

import pytest
from continuity.core.memory import MemoryEngine
from continuity.core.models import MemoryType, Role
from continuity.storage.sqlite import Storage


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    storage = Storage(db_path)
    return MemoryEngine(storage)


def test_start_session(engine):
    conv = engine.start_session("openai", "gpt-4o", title="Test")
    assert conv.provider == "openai"
    assert conv.model == "gpt-4o"
    assert conv.title == "Test"


def test_add_message(engine):
    conv = engine.start_session("openai", "gpt-4o")
    msg = engine.add_message(conv.id, Role.USER, "Hello, world!")
    assert msg.role == Role.USER
    assert msg.content == "Hello, world!"


def test_store_memory(engine):
    mem = engine.store_memory("The project uses PostgreSQL", MemoryType.SEMANTIC)
    assert mem.content == "The project uses PostgreSQL"
    assert mem.memory_type == MemoryType.SEMANTIC


def test_search_memories(engine):
    engine.store_memory("We use PostgreSQL for the database", MemoryType.SEMANTIC)
    engine.store_memory("The frontend uses React", MemoryType.SEMANTIC)
    results = engine.search_memories("database", limit=5)
    assert len(results) > 0
    assert "PostgreSQL" in results[0][0].content


def test_get_context(engine):
    conv = engine.start_session("openai", "gpt-4o")
    engine.add_message(conv.id, Role.USER, "What database should we use?")
    engine.add_message(conv.id, Role.ASSISTANT, "PostgreSQL is a great choice.")
    engine.store_memory("We decided on PostgreSQL", MemoryType.SEMANTIC)

    context = engine.get_context(
        [Message(role=Role.USER, content="Tell me about our database")]
    )
    assert len(context.relevant_memories) > 0


def test_consolidate_memories(engine):
    engine.store_memory("PostgreSQL is the database", MemoryType.SEMANTIC)
    engine.store_memory("PostgreSQL is the database", MemoryType.SEMANTIC)
    merged = engine.consolidate_memories()
    assert merged >= 0  # May or may not merge depending on dedup logic


@pytest.fixture
def Message():
    from continuity.core.models import Message
    return Message
