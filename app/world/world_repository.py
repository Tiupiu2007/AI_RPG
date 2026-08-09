"""Persistence for the world state.

This module owns the SQLite storage used by WorldState. The WorldState model
itself remains independent from storage, so database details do not leak into
world logic.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .world_state import WorldState


class WorldRepository:
    """SQLite repository for persistent WorldState objects."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        """Create the world-state table when it does not exist."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS world_states (
                    world_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save(self, world: WorldState) -> None:
        """Insert or replace a complete world state."""
        world.update()
        state_json = json.dumps(
            world.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO world_states (
                    world_id,
                    name,
                    description,
                    state_json,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(world_id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    world.world_id,
                    world.name,
                    world.description,
                    state_json,
                    world.updated_at,
                ),
            )
            connection.commit()

    def load(self, world_id: str) -> WorldState | None:
        """Load one world by its identifier."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM world_states WHERE world_id = ?",
                (world_id,),
            ).fetchone()

        if row is None:
            return None

        try:
            data: Any = json.loads(row["state_json"])
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Lo stato del mondo '{world_id}' non contiene JSON valido."
            ) from error

        return WorldState.from_dict(data)

    def delete(self, world_id: str) -> bool:
        """Delete a world and return whether it existed."""
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM world_states WHERE world_id = ?",
                (world_id,),
            )
            connection.commit()
            return cursor.rowcount > 0

    def exists(self, world_id: str) -> bool:
        """Return whether a world exists."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM world_states WHERE world_id = ? LIMIT 1",
                (world_id,),
            ).fetchone()
        return row is not None

    def list_worlds(self) -> list[dict[str, str]]:
        """Return basic information for all stored worlds."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT world_id, name, description, updated_at
                FROM world_states
                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [
            {
                "world_id": row["world_id"],
                "name": row["name"],
                "description": row["description"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
