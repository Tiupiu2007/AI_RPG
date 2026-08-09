# app/database/characters_db.py

import sqlite3
from pathlib import Path

from app.characters.characters_identity import CharacterIdentity


# =========================================================
# DATABASE
# =========================================================

DATABASE_PATH = Path("data/characters.db")


# =========================================================
# CONNESSIONE
# =========================================================

def get_connection() -> sqlite3.Connection:

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# INIZIALIZZAZIONE
# =========================================================

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


# =========================================================
# SALVATAGGIO
# =========================================================

def save_identity(
    identity: CharacterIdentity
) -> int:

    if not isinstance(
        identity,
        CharacterIdentity
    ):

        raise TypeError(
            "identity deve essere "
            "un CharacterIdentity."
        )

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            INSERT INTO characters (
                name,
                surname,
                nickname,
                age,
                birth_date,
                sex,
                race,
                physical_description,
                appearance
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identity.name,
                identity.surname,
                identity.nickname,
                identity.age,
                identity.birth_date,
                identity.sex,
                identity.race,
                identity.physical_description,
                identity.appearance,
            )
        )

        connection.commit()

        return cursor.lastrowid

    finally:

        connection.close()


# =========================================================
# LETTURA
# =========================================================

def get_identity(
    character_id: int
) -> CharacterIdentity | None:

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                name,
                surname,
                nickname,
                age,
                birth_date,
                sex,
                race,
                physical_description,
                appearance

            FROM characters

            WHERE id = ?
            """,
            (character_id,)
        ).fetchone()

    finally:

        connection.close()

    if row is None:
        return None

    return CharacterIdentity(
        name=row["name"],
        surname=row["surname"],
        nickname=row["nickname"],
        age=row["age"],
        birth_date=row["birth_date"],
        sex=row["sex"],
        race=row["race"],
        physical_description=row[
            "physical_description"
        ],
        appearance=row["appearance"],
    )


# =========================================================
# AGGIORNAMENTO
# =========================================================

def update_identity(
    character_id: int,
    identity: CharacterIdentity
) -> None:

    if not isinstance(
        identity,
        CharacterIdentity
    ):

        raise TypeError(
            "identity deve essere "
            "un CharacterIdentity."
        )

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            UPDATE characters

            SET
                name = ?,
                surname = ?,
                nickname = ?,
                age = ?,
                birth_date = ?,
                sex = ?,
                race = ?,
                physical_description = ?,
                appearance = ?

            WHERE id = ?
            """,
            (
                identity.name,
                identity.surname,
                identity.nickname,
                identity.age,
                identity.birth_date,
                identity.sex,
                identity.race,
                identity.physical_description,
                identity.appearance,
                character_id,
            )
        )

        connection.commit()

        if cursor.rowcount == 0:

            raise ValueError(
                f"Personaggio con ID "
                f"{character_id} non trovato."
            )

    finally:

        connection.close()


# =========================================================
# ELIMINAZIONE
# =========================================================

def delete_character(
    character_id: int
) -> None:

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            DELETE FROM characters

            WHERE id = ?
            """,
            (character_id,)
        )

        connection.commit()

        if cursor.rowcount == 0:

            raise ValueError(
                f"Personaggio con ID "
                f"{character_id} non trovato."
            )

    finally:

        connection.close()