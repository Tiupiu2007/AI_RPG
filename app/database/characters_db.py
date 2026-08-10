import json
import sqlite3
from pathlib import Path
from typing import Any

from app.characters.characters import Character
from app.characters.characters_identity import CharacterIdentity
from app.characters.characters_languages import CharacterLanguage

DATABASE_PATH = Path("data/characters.db")


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database() -> None:
    connection = get_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                surname TEXT NOT NULL DEFAULT '',
                nickname TEXT NOT NULL DEFAULT '',
                age INTEGER NOT NULL,
                birth_date TEXT NOT NULL,
                sex TEXT NOT NULL,
                race TEXT NOT NULL,
                physical_description TEXT NOT NULL,
                appearance TEXT NOT NULL,
                extra_data TEXT NOT NULL DEFAULT '{}'
            )
        """)

        columns = {row["name"] for row in connection.execute("PRAGMA table_info(characters)")}
        if "extra_data" not in columns:
            connection.execute("ALTER TABLE characters ADD COLUMN extra_data TEXT NOT NULL DEFAULT '{}'")

        connection.execute("""
            CREATE TABLE IF NOT EXISTS character_languages (
                character_id INTEGER NOT NULL,
                language_id TEXT NOT NULL,
                name TEXT NOT NULL,
                comprehension REAL NOT NULL DEFAULT 0.0,
                speaking REAL NOT NULL DEFAULT 0.0,
                writing REAL NOT NULL DEFAULT 0.0,
                PRIMARY KEY (character_id, language_id),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                memory_type TEXT NOT NULL DEFAULT 'evento',
                content TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
                secret INTEGER NOT NULL DEFAULT 0 CHECK (secret IN (0, 1)),
                source_event_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_character_importance
            ON memories(character_id, importance DESC, created_at DESC)
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_character_id
            ON events(character_id, id DESC)
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                character_a_id INTEGER NOT NULL,
                character_b_id INTEGER NOT NULL,
                trust INTEGER NOT NULL DEFAULT 0 CHECK (trust BETWEEN -100 AND 100),
                affection INTEGER NOT NULL DEFAULT 0 CHECK (affection BETWEEN -100 AND 100),
                respect INTEGER NOT NULL DEFAULT 0 CHECK (respect BETWEEN -100 AND 100),
                hostility INTEGER NOT NULL DEFAULT 0 CHECK (hostility BETWEEN -100 AND 100),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_a_id, character_b_id),
                FOREIGN KEY (character_a_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (character_b_id) REFERENCES characters(id) ON DELETE CASCADE,
                CHECK (character_a_id != character_b_id)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_character_b
            ON relationships(character_b_id)
        """)

        connection.commit()
    finally:
        connection.close()


def _identity_values(identity: CharacterIdentity):
    if not isinstance(identity, CharacterIdentity):
        raise TypeError("identity deve essere un CharacterIdentity.")
    return (
        identity.name, identity.surname, identity.nickname, identity.age,
        identity.birth_date, identity.sex, identity.race,
        identity.physical_description, identity.appearance,
    )


def save_identity(identity: CharacterIdentity, extra_data: dict | None = None) -> int:
    values = _identity_values(identity)
    payload = json.dumps(extra_data or {}, ensure_ascii=False)
    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO characters (
                name, surname, nickname, age, birth_date, sex, race,
                physical_description, appearance, extra_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (*values, payload))
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def _row_to_identity(row) -> CharacterIdentity:
    return CharacterIdentity(
        name=row["name"], surname=row["surname"], nickname=row["nickname"],
        age=row["age"], birth_date=row["birth_date"], sex=row["sex"],
        race=row["race"], physical_description=row["physical_description"],
        appearance=row["appearance"],
    )


def get_identity(character_id: int) -> CharacterIdentity | None:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT name, surname, nickname, age, birth_date, sex, race, physical_description, appearance FROM characters WHERE id = ?",
            (character_id,),
        ).fetchone()
    finally:
        connection.close()
    return None if row is None else _row_to_identity(row)


def _row_extra(row) -> dict:
    try:
        value = json.loads(row["extra_data"] or "{}")
        return value if isinstance(value, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def get_all_identities() -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT id, name, surname, nickname, age, birth_date, sex, race,
                   physical_description, appearance
            FROM characters ORDER BY id DESC
        """).fetchall()
    finally:
        connection.close()

    return [{"id": row["id"], "identity": {
        "name": row["name"], "surname": row["surname"], "nickname": row["nickname"],
        "age": row["age"], "birth_date": row["birth_date"], "sex": row["sex"],
        "race": row["race"], "physical_description": row["physical_description"],
        "appearance": row["appearance"],
    }} for row in rows]


def update_identity(character_id: int, identity: CharacterIdentity, extra_data: dict | None = None) -> None:
    values = _identity_values(identity)
    connection = get_connection()
    try:
        if extra_data is None:
            cursor = connection.execute("""
                UPDATE characters SET name=?, surname=?, nickname=?, age=?, birth_date=?,
                sex=?, race=?, physical_description=?, appearance=? WHERE id=?
            """, (*values, character_id))
        else:
            cursor = connection.execute("""
                UPDATE characters SET name=?, surname=?, nickname=?, age=?, birth_date=?,
                sex=?, race=?, physical_description=?, appearance=?, extra_data=? WHERE id=?
            """, (*values, json.dumps(extra_data, ensure_ascii=False), character_id))
        connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    finally:
        connection.close()


def save_languages(character_id: int, languages: list[CharacterLanguage]) -> None:
    if not isinstance(languages, list):
        raise TypeError("languages deve essere una lista.")
    connection = get_connection()
    try:
        connection.execute("DELETE FROM character_languages WHERE character_id = ?", (character_id,))
        for language in languages:
            if not isinstance(language, CharacterLanguage):
                raise TypeError("Ogni lingua deve essere un CharacterLanguage.")
            connection.execute("""
                INSERT INTO character_languages (
                    character_id, language_id, name, comprehension, speaking, writing
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                character_id, language.language_id, language.name,
                language.comprehension, language.speaking, language.writing,
            ))
        connection.commit()
    finally:
        connection.close()


def get_languages(character_id: int) -> list[CharacterLanguage]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT language_id, name, comprehension, speaking, writing
            FROM character_languages WHERE character_id = ? ORDER BY rowid
        """, (character_id,)).fetchall()
    finally:
        connection.close()
    return [CharacterLanguage(
        language_id=row["language_id"], name=row["name"],
        comprehension=row["comprehension"], speaking=row["speaking"], writing=row["writing"],
    ) for row in rows]


def save_character(identity: CharacterIdentity, languages: list[CharacterLanguage], extra_data: dict | None = None, character_id: int | None = None) -> int:
    if character_id is None:
        character_id = save_identity(identity, extra_data)
    else:
        update_identity(character_id, identity, extra_data)
    save_languages(character_id, languages)
    return character_id


def save_character_model(character: Character, character_id: int | None = None) -> int:
    if not isinstance(character, Character):
        raise TypeError("character deve essere un Character.")
    payload: dict[str, Any] = dict(character.extra)
    payload["inventory"] = character.inventory.to_dict()
    payload["money"] = character.money.to_dict()
    payload["magic"] = character.magic.to_dict()
    return save_character(character.identity, character.languages, payload, character_id)


def get_character(character_id: int) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    return {
        "id": character_id,
        "identity": _row_to_identity(row),
        "languages": get_languages(character_id),
        "extra": _row_extra(row),
    }


def delete_character(character_id: int) -> None:
    connection = get_connection()
    try:
        cursor = connection.execute("DELETE FROM characters WHERE id = ?", (character_id,))
        connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    finally:
        connection.close()
