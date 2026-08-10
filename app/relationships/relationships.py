from __future__ import annotations

from typing import Any

from app.database.characters_db import get_connection

RELATIONSHIP_FIELDS = ("trust", "affection", "respect", "hostility")


def _clamp(value: int) -> int:
    return max(-100, min(100, int(value)))


def _row_to_dict(row) -> dict[str, Any]:
    return {
        "character_a_id": row["character_a_id"],
        "character_b_id": row["character_b_id"],
        "trust": row["trust"],
        "affection": row["affection"],
        "respect": row["respect"],
        "hostility": row["hostility"],
        "updated_at": row["updated_at"],
    }


def ensure_relationship(character_a_id: int, character_b_id: int) -> dict[str, Any]:
    if character_a_id == character_b_id:
        raise ValueError("Un personaggio non può avere una relazione con se stesso.")
    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT OR IGNORE INTO relationships
            (character_a_id, character_b_id, trust, affection, respect, hostility, updated_at)
            VALUES (?, ?, 0, 0, 0, 0, CURRENT_TIMESTAMP)
            """,
            (character_a_id, character_b_id),
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM relationships WHERE character_a_id = ? AND character_b_id = ?",
            (character_a_id, character_b_id),
        ).fetchone()
    finally:
        connection.close()
    return _row_to_dict(row)


def create_relationship(character_a_id: int, character_b_id: int, **values: int) -> dict[str, Any]:
    relation = ensure_relationship(character_a_id, character_b_id)
    if values:
        return change_relationship(character_a_id, character_b_id, **values)
    return relation


def get_relationship(character_a_id: int, character_b_id: int) -> dict[str, Any] | None:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM relationships WHERE character_a_id = ? AND character_b_id = ?",
            (character_a_id, character_b_id),
        ).fetchone()
    finally:
        connection.close()
    return None if row is None else _row_to_dict(row)


def get_character_relationships(character_id: int) -> list[dict[str, Any]]:
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT * FROM relationships WHERE character_a_id = ? ORDER BY updated_at DESC",
            (character_id,),
        ).fetchall()
    finally:
        connection.close()
    return [_row_to_dict(row) for row in rows]


def change_relationship(character_a_id: int, character_b_id: int, **deltas: int) -> dict[str, Any]:
    if character_a_id == character_b_id:
        raise ValueError("Un personaggio non può modificare la relazione con se stesso.")
    unknown = set(deltas) - set(RELATIONSHIP_FIELDS)
    if unknown:
        raise ValueError(f"Campi relazione non consentiti: {sorted(unknown)}")
    for field, delta in deltas.items():
        if not isinstance(delta, int) or isinstance(delta, bool) or not -30 <= delta <= 30:
            raise ValueError(f"{field} deve essere una variazione intera tra -30 e 30.")

    current = ensure_relationship(character_a_id, character_b_id)
    updated = {
        field: _clamp(int(current[field]) + int(deltas.get(field, 0)))
        for field in RELATIONSHIP_FIELDS
    }
    connection = get_connection()
    try:
        connection.execute(
            """
            UPDATE relationships
            SET trust=?, affection=?, respect=?, hostility=?, updated_at=CURRENT_TIMESTAMP
            WHERE character_a_id=? AND character_b_id=?
            """,
            (*[updated[field] for field in RELATIONSHIP_FIELDS], character_a_id, character_b_id),
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM relationships WHERE character_a_id = ? AND character_b_id = ?",
            (character_a_id, character_b_id),
        ).fetchone()
    finally:
        connection.close()
    return _row_to_dict(row)
