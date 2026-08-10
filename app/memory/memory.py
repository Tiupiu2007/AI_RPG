from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.database.characters_db import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_memory(
    character_id: int,
    content: str,
    memory_type: str = "evento",
    importance: int = 5,
    secret: bool = False,
    source_event_id: int | None = None,
) -> int:
    """Salva una memoria persistente senza creare duplicati identici."""
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("character_id non valido.")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Il contenuto della memoria non può essere vuoto.")
    if not 1 <= int(importance) <= 10:
        raise ValueError("importance deve essere compreso tra 1 e 10.")

    content = " ".join(content.strip().split())
    memory_type = str(memory_type or "evento").strip() or "evento"

    connection = get_connection()
    try:
        # La stessa informazione non deve essere salvata più volte solo perché
        # è stata rilevata da eventi o turni diversi.
        existing = connection.execute(
            """
            SELECT id
            FROM memories
            WHERE character_id = ? AND memory_type = ? AND content = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (character_id, memory_type, content),
        ).fetchone()
        if existing is not None:
            return int(existing["id"])

        cursor = connection.execute(
            """
            INSERT INTO memories (
                character_id, memory_type, content, importance, secret,
                source_event_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                character_id,
                memory_type,
                content,
                int(importance),
                1 if secret else 0,
                source_event_id,
                _now(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def get_character_memories(
    character_id: int,
    limit: int = 20,
    include_secrets: bool = True,
) -> list[dict[str, Any]]:
    """Restituisce poche memorie utili, privilegiando importanza e recenza."""
    limit = max(1, min(int(limit), 100))
    secret_clause = "" if include_secrets else "AND secret = 0"
    connection = get_connection()
    try:
        rows = connection.execute(
            f"""
            SELECT id, character_id, memory_type, content, importance,
                   secret, source_event_id, created_at
            FROM memories
            WHERE character_id = ? {secret_clause}
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
            """,
            (character_id, limit),
        ).fetchall()
    finally:
        connection.close()

    return [
        {
            "id": row["id"],
            "character_id": row["character_id"],
            "memory_type": row["memory_type"],
            "content": row["content"],
            "importance": row["importance"],
            "secret": bool(row["secret"]),
            "source_event_id": row["source_event_id"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def create_event(
    character_id: int,
    event_type: str,
    payload: dict[str, Any],
) -> int:
    if not isinstance(payload, dict):
        raise ValueError("payload evento deve essere un dizionario.")

    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO events (character_id, event_type, payload, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                character_id,
                str(event_type),
                json.dumps(payload, ensure_ascii=False, default=str),
                _now(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def get_recent_events(character_id: int, limit: int = 30) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, character_id, event_type, payload, created_at
            FROM events
            WHERE character_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (character_id, limit),
        ).fetchall()
    finally:
        connection.close()

    result = []
    for row in reversed(rows):
        try:
            payload = json.loads(row["payload"] or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
        result.append({
            "id": row["id"],
            "character_id": row["character_id"],
            "event_type": row["event_type"],
            "payload": payload,
            "created_at": row["created_at"],
        })
    return result
