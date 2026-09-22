"""Tests for storage layer."""

import pytest
from continuity.storage.sqlite import Storage
from continuity.core.models import (
    Conversation,
    Memory,
    MemoryType,
    Message,
    Role,
    TemporalFact,
)


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test.db"
    return Storage(db_path)


def test_save_and_get_conversation(storage):
    conv = Conversation(provider="openai", model="gpt-4o", title="Test")
    storage.save_conversation(conv)
    retrieved = storage.get_conversation(conv.id)
    assert retrieved is not None
    assert retrieved.provider == "openai"
    assert retrieved.title == "Test"


def test_list_conversations(storage):
    for i in range(5):
        conv = Conversation(provider="openai", model="gpt-4o", title=f"Session {i}")
        storage.save_conversation(conv)
    convs = storage.list_conversations(limit=3)
    assert len(convs) == 3


def test_save_message(storage):
    conv = Conversation(provider="openai", model="gpt-4o")
    storage.save_conversation(conv)
    msg = Message(role=Role.USER, content="Hello!")
    storage.save_message(conv.id, msg)
    messages = storage.get_messages(conv.id)
    assert len(messages) == 1
    assert messages[0].content == "Hello!"


def test_save_memory(storage):
    mem = Memory(content="Test memory", memory_type=MemoryType.SEMANTIC)
    storage.save_memory(mem)
    retrieved = storage.get_memory(mem.id)
    assert retrieved is not None
    assert retrieved.content == "Test memory"


def test_list_memories(storage):
    for i in range(3):
        mem = Memory(content=f"Memory {i}", memory_type=MemoryType.SEMANTIC)
        storage.save_memory(mem)
    memories = storage.list_memories()
    assert len(memories) == 3


def test_delete_memory(storage):
    mem = Memory(content="To delete", memory_type=MemoryType.EPISODIC)
    storage.save_memory(mem)
    storage.delete_memory(mem.id)
    assert storage.get_memory(mem.id) is None


def test_stats(storage):
    stats = storage.get_stats()
    assert "conversations" in stats
    assert "messages" in stats
    assert "memories" in stats
