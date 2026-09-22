"""SQLite storage layer for Continuity."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from continuity.core.models import (
    Conversation,
    Memory,
    MemoryType,
    Message,
    Role,
    TemporalFact,
)


class Storage:
    """Local SQLite storage for conversations and memories."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            from platformdirs import user_data_dir
            db_path = Path(user_data_dir("continuity")) / "continuity.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self) -> None:
        self.conn.executescript(_SCHEMA)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # --- Conversations ---

    def save_conversation(self, conv: Conversation) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO conversations
               (id, provider, model, title, summary, created_at, updated_at,
                message_count, total_tokens, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                conv.id, conv.provider, conv.model, conv.title, conv.summary,
                conv.created_at.isoformat(), conv.updated_at.isoformat(),
                conv.message_count, conv.total_tokens, json.dumps(conv.metadata),
            ),
        )
        self.conn.commit()

    def get_conversation(self, conv_id: str) -> Conversation | None:
        row = self.conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_conversation(row)

    def list_conversations(self, limit: int = 20) -> list[Conversation]:
        rows = self.conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_conversation(r) for r in rows]

    def _row_to_conversation(self, row: sqlite3.Row) -> Conversation:
        return Conversation(
            id=row["id"],
            provider=row["provider"],
            model=row["model"],
            title=row["title"],
            summary=row["summary"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            message_count=row["message_count"],
            total_tokens=row["total_tokens"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    # --- Messages ---

    def save_message(self, conv_id: str, msg: Message) -> None:
        self.conn.execute(
            """INSERT INTO messages (id, conversation_id, role, content, created_at, tokens, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                msg.id, conv_id, msg.role.value, msg.content,
                msg.created_at.isoformat(), msg.tokens,
                json.dumps(msg.metadata),
            ),
        )
        self.conn.execute(
            "UPDATE conversations SET message_count = message_count + 1, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), conv_id),
        )
        self.conn.commit()

    def get_messages(self, conv_id: str, limit: int = 100) -> list[Message]:
        rows = self.conn.execute(
            """SELECT * FROM messages WHERE conversation_id = ?
               ORDER BY created_at ASC LIMIT ?""",
            (conv_id, limit),
        ).fetchall()
        return [self._row_to_message(r) for r in rows]

    def get_recent_messages(self, limit: int = 20) -> list[Message]:
        rows = self.conn.execute(
            """SELECT m.* FROM messages m
               JOIN conversations c ON m.conversation_id = c.id
               ORDER BY m.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [self._row_to_message(r) for r in reversed(rows)]

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        return Message(
            id=row["id"],
            role=Role(row["role"]),
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
            tokens=row["tokens"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    # --- Memories ---

    def save_memory(self, memory: Memory) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO memories
               (id, content, memory_type, confidence, source_conversation_id,
                created_at, expires_at, metadata, embedding)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory.id, memory.content, memory.memory_type.value,
                memory.confidence, memory.source_conversation_id,
                memory.created_at.isoformat(),
                memory.expires_at.isoformat() if memory.expires_at else None,
                json.dumps(memory.metadata),
                None,  # Embedding set separately
            ),
        )
        self.conn.commit()

    def update_memory_embedding(self, memory_id: str, embedding: list[float]) -> None:
        import numpy as np
        blob = np.array(embedding, dtype=np.float32).tobytes()
        self.conn.execute(
            "UPDATE memories SET embedding = ? WHERE id = ?",
            (blob, memory_id),
        )
        self.conn.commit()

    def get_memory(self, memory_id: str) -> Memory | None:
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_memory(row)

    def list_memories(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 100,
    ) -> list[Memory]:
        if memory_type:
            rows = self.conn.execute(
                """SELECT * FROM memories
                   WHERE memory_type = ? AND (expires_at IS NULL OR expires_at > ?)
                   ORDER BY created_at DESC LIMIT ?""",
                (memory_type.value, datetime.now().isoformat(), limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM memories
                   WHERE expires_at IS NULL OR expires_at > ?
                   ORDER BY created_at DESC LIMIT ?""",
                (datetime.now().isoformat(), limit),
            ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def search_memories_by_embedding(
        self,
        query_embedding: list[float],
        limit: int = 10,
        memory_type: MemoryType | None = None,
    ) -> list[tuple[Memory, float]]:
        """Search memories by cosine similarity. Returns (memory, score) tuples."""
        import numpy as np

        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        results: list[tuple[Memory, float]] = []

        if memory_type:
            rows = self.conn.execute(
                """SELECT * FROM memories
                   WHERE embedding IS NOT NULL AND memory_type = ?
                   AND (expires_at IS NULL OR expires_at > ?)""",
                (memory_type.value, datetime.now().isoformat()),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM memories
                   WHERE embedding IS NOT NULL
                   AND (expires_at IS NULL OR expires_at > ?)""",
                (datetime.now().isoformat(),),
            ).fetchall()

        for row in rows:
            blob = row["embedding"]
            if blob is None:
                continue
            mem_vec = np.frombuffer(blob, dtype=np.float32)
            mem_norm = np.linalg.norm(mem_vec)
            if mem_norm == 0:
                continue
            score = float(np.dot(query_vec, mem_vec) / (query_norm * mem_norm))
            results.append((self._row_to_memory(row), score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def delete_memory(self, memory_id: str) -> None:
        self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        return Memory(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            confidence=row["confidence"],
            source_conversation_id=row["source_conversation_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=(
                datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            ),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    # --- Temporal Facts ---

    def save_temporal_fact(self, fact: TemporalFact) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO temporal_facts
               (id, subject, predicate, object, valid_from, valid_to,
                replaced_by, confidence, source_conversation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fact.id, fact.subject, fact.predicate, fact.object,
                fact.valid_from.isoformat(),
                fact.valid_to.isoformat() if fact.valid_to else None,
                fact.replaced_by, fact.confidence, fact.source_conversation_id,
            ),
        )
        self.conn.commit()

    def get_active_facts(self, subject: str | None = None) -> list[TemporalFact]:
        if subject:
            rows = self.conn.execute(
                """SELECT * FROM temporal_facts
                   WHERE subject = ? AND valid_to IS NULL
                   ORDER BY valid_from DESC""",
                (subject,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM temporal_facts
                   WHERE valid_to IS NULL
                   ORDER BY valid_from DESC"""
            ).fetchall()
        return [self._row_to_temporal_fact(r) for r in rows]

    def _row_to_temporal_fact(self, row: sqlite3.Row) -> TemporalFact:
        return TemporalFact(
            id=row["id"],
            subject=row["subject"],
            predicate=row["predicate"],
            object=row["object"],
            valid_from=datetime.fromisoformat(row["valid_from"]),
            valid_to=datetime.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
            replaced_by=row["replaced_by"],
            confidence=row["confidence"],
            source_conversation_id=row["source_conversation_id"],
        )

    # --- Stats ---

    def get_stats(self) -> dict[str, Any]:
        conv_count = self.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        msg_count = self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        mem_count = self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        fact_count = self.conn.execute("SELECT COUNT(*) FROM temporal_facts").fetchone()[0]
        return {
            "conversations": conv_count,
            "messages": msg_count,
            "memories": mem_count,
            "temporal_facts": fact_count,
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
        }


_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    tokens INTEGER,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source_conversation_id TEXT REFERENCES conversations(id),
    created_at TEXT NOT NULL,
    expires_at TEXT,
    metadata TEXT DEFAULT '{}',
    embedding BLOB
);

CREATE TABLE IF NOT EXISTS temporal_facts (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    replaced_by TEXT REFERENCES temporal_facts(id),
    confidence REAL DEFAULT 1.0,
    source_conversation_id TEXT REFERENCES conversations(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_temporal_subject ON temporal_facts(subject);
CREATE INDEX IF NOT EXISTS idx_temporal_active ON temporal_facts(valid_to);
"""
