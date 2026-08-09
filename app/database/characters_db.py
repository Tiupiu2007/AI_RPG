import sqlite3
from pathlib import Path

from app.characters.characters_identity import CharacterIdentity
from app.characters.characters_languages import CharacterLanguage

DATABASE_PATH = Path("data/characters.db")


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
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
                appearance TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS character_languages (
                character_id INTEGER NOT NULL,
                language_id TEXT NOT NULL,
                name TEXT NOT NULL,
                comprehension REAL NOT NULL DEFAULT 0.0,
                speaking REAL NOT NULL DEFAULT 0.0,
                writing REAL NOT NULL DEFAULT 0.0,
                PRIMARY KEY (character_id, language_id),
                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE
            )
        """)

        connection.commit()
    finally:
        connection.close()


def save_identity(identity: CharacterIdentity) -> int:
    if not isinstance(identity, CharacterIdentity):
        raise TypeError("identity deve essere un CharacterIdentity.")

    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO characters (
                name, surname, nickname, age, birth_date, sex, race,
                physical_description, appearance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            identity.name, identity.surname, identity.nickname,
            identity.age, identity.birth_date, identity.sex, identity.race,
            identity.physical_description, identity.appearance,
        ))
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def _row_to_identity(row) -> CharacterIdentity:
    return CharacterIdentity(
        name=row["name"],
        surname=row["surname"],
        nickname=row["nickname"],
        age=row["age"],
        birth_date=row["birth_date"],
        sex=row["sex"],
        race=row["race"],
        physical_description=row["physical_description"],
        appearance=row["appearance"],
    )


def get_identity(character_id: int) -> CharacterIdentity | None:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT name, surname, nickname, age, birth_date, sex, race, physical_description, appearance FROM characters WHERE id = ?",
            (character_id,)
        ).fetchone()
    finally:
        connection.close()

    return None if row is None else _row_to_identity(row)


def get_all_identities() -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT id, name, surname, nickname, age, birth_date, sex, race,
                   physical_description, appearance
            FROM characters
            ORDER BY id DESC
        """).fetchall()
    finally:
        connection.close()

    return [
        {
            "id": row["id"],
            "identity": {
                "name": row["name"],
                "surname": row["surname"],
                "nickname": row["nickname"],
                "age": row["age"],
                "birth_date": row["birth_date"],
                "sex": row["sex"],
                "race": row["race"],
                "physical_description": row["physical_description"],
                "appearance": row["appearance"],
            }
        }
        for row in rows
    ]


def update_identity(character_id: int, identity: CharacterIdentity) -> None:
    if not isinstance(identity, CharacterIdentity):
        raise TypeError("identity deve essere un CharacterIdentity.")

    connection = get_connection()
    try:
        cursor = connection.execute("""
            UPDATE characters SET
                name = ?, surname = ?, nickname = ?, age = ?, birth_date = ?,
                sex = ?, race = ?, physical_description = ?, appearance = ?
            WHERE id = ?
        """, (
            identity.name, identity.surname, identity.nickname,
            identity.age, identity.birth_date, identity.sex, identity.race,
            identity.physical_description, identity.appearance, character_id,
        ))
        connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    finally:
        connection.close()


def save_languages(character_id: int, languages: list[CharacterLanguage]) -> None:
    if not isinstance(character_id, int):
        raise TypeError("character_id deve essere un intero.")

    if not isinstance(languages, list):
        raise TypeError("languages deve essere una lista.")

    connection = get_connection()
    try:
        connection.execute(
            "DELETE FROM character_languages WHERE character_id = ?",
            (character_id,)
        )

        for language in languages:
            if not isinstance(language, CharacterLanguage):
                raise TypeError("Ogni lingua deve essere un CharacterLanguage.")

            connection.execute("""
                INSERT INTO character_languages (
                    character_id, language_id, name,
                    comprehension, speaking, writing
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                character_id,
                language.language_id,
                language.name,
                language.comprehension,
                language.speaking,
                language.writing,
            ))

        connection.commit()
    finally:
        connection.close()


def get_languages(character_id: int) -> list[CharacterLanguage]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT language_id, name, comprehension, speaking, writing
            FROM character_languages
            WHERE character_id = ?
            ORDER BY rowid
        """, (character_id,)).fetchall()
    finally:
        connection.close()

    return [
        CharacterLanguage(
            language_id=row["language_id"],
            name=row["name"],
            comprehension=row["comprehension"],
            speaking=row["speaking"],
            writing=row["writing"],
        )
        for row in rows
    ]


def save_character(
    identity: CharacterIdentity,
    languages: list[CharacterLanguage],
    character_id: int | None = None,
) -> int:
    if character_id is None:
        character_id = save_identity(identity)
    else:
        update_identity(character_id, identity)

    save_languages(character_id, languages)
    return character_id


def get_character(character_id: int) -> dict | None:
    identity = get_identity(character_id)
    if identity is None:
        return None

    return {
        "id": character_id,
        "identity": identity,
        "languages": get_languages(character_id),
    }


def delete_character(character_id: int) -> None:
    connection = get_connection()
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.execute(
            "DELETE FROM characters WHERE id = ?",
            (character_id,)
        )
        connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    finally:
        connection.close()
