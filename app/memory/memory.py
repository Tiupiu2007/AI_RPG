from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.database.characters_db import get_connection


DEFAULT_MEMORY_LIMIT = 20
MAX_MEMORY_LIMIT = 100
DEFAULT_EVENT_LIMIT = 20
MAX_EVENT_LIMIT = 100


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bounded_limit(value: int, default: int, maximum: int) -> int:
    """Normalizza un limite SQL evitando valori negativi o eccessivi."""
    try:
        value = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Il limite deve essere un intero.") from error
    return max(1, min(value, maximum))


def create_memory(
    character_id: int,
    content: str,
    memory_type: str = "evento",
    importance: int = 5,
    secret: bool = False,
    source_event_id: int | None = None,
) -> int:
    """Salva una memoria persistente evitando duplicati identici."""
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("character_id non valido.")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Il contenuto della memoria non può essere vuoto.")
    if not isinstance(importance, int) or isinstance(importance, bool):
        raise ValueError("importance deve essere un intero.")
    if not 1 <= importance <= 10:
        raise ValueError("importance deve essere compreso tra 1 e 10.")
    if not isinstance(secret, bool):
        raise ValueError("secret deve essere booleano.")
    if source_event_id is not None and (
        not isinstance(source_event_id, int) or isinstance(source_event_id, bool)
    ):
        raise ValueError("source_event_id non valido.")

    content = " ".join(content.strip().split())
    memory_type = str(memory_type or "evento").strip() or "evento"

    connection = get_connection()
    try:
        # Una stessa informazione non deve moltiplicarsi a ogni turno.
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
                importance,
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
    limit: int = DEFAULT_MEMORY_LIMIT,
    include_secrets: bool = True,
) -> list[dict[str, Any]]:
    """Restituisce le memorie più importanti e recenti del personaggio."""
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("character_id non valido.")
    if not isinstance(include_secrets, bool):
        raise ValueError("include_secrets deve essere booleano.")

    limit = _bounded_limit(limit, DEFAULT_MEMORY_LIMIT, MAX_MEMORY_LIMIT)
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
    """Registra un evento persistente del game engine."""
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("character_id non valido.")
    if not isinstance(event_type, str) or not event_type.strip():
        raise ValueError("event_type non può essere vuoto.")
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
                event_type.strip(),
                json.dumps(payload, ensure_ascii=False, default=str),
                _now(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def get_recent_events(
    character_id: int,
    limit: int = DEFAULT_EVENT_LIMIT,
) -> list[dict[str, Any]]:
    """Restituisce gli eventi in ordine cronologico, dal più vecchio al più recente."""
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("character_id non valido.")

    limit = _bounded_limit(limit, DEFAULT_EVENT_LIMIT, MAX_EVENT_LIMIT)

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

    result: list[dict[str, Any]] = []
    for row in reversed(rows):
        try:
            payload = json.loads(row["payload"] or "{}")
        except (TypeError, json.JSONDecodeError):
            # Un evento corrotto non deve impedire il caricamento del personaggio.
            payload = {}
        result.append({
            "id": row["id"],
            "character_id": row["character_id"],
            "event_type": row["event_type"],
            "payload": payload,
            "created_at": row["created_at"],
        })
    return result
