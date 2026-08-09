import sqlite3
from pathlib import Path

from app.characters.characters_identity import CharacterIdentity

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


def delete_character(character_id: int) -> None:
    connection = get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM characters WHERE id = ?",
            (character_id,)
        )
        connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    finally:
        connection.close()
