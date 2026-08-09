import sqlite3
from pathlib import Path


DATABASE_PATH = Path("saves/game.db")

MAX_LEVEL = 999
MAX_STAT = 999


def get_connection():

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                description TEXT NOT NULL DEFAULT ''
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_connections (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                location_a_id INTEGER NOT NULL,

                location_b_id INTEGER NOT NULL,

                connection_type TEXT NOT NULL DEFAULT 'passage',

                description TEXT NOT NULL DEFAULT '',

                FOREIGN KEY (location_a_id)
                    REFERENCES locations(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (location_b_id)
                    REFERENCES locations(id)
                    ON DELETE CASCADE,

                UNIQUE (
                    location_a_id,
                    location_b_id
                )
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                surname TEXT,

                age INTEGER,

                sex TEXT,

                gender TEXT,

                species TEXT NOT NULL DEFAULT 'human',

                description TEXT NOT NULL DEFAULT '',

                appearance TEXT NOT NULL DEFAULT '',

                voice TEXT NOT NULL DEFAULT '',

                location_id INTEGER,

                alive INTEGER NOT NULL DEFAULT 1,

                FOREIGN KEY (location_id)
                    REFERENCES locations(id)
                    ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_progression (

                character_id INTEGER PRIMARY KEY,

                level INTEGER NOT NULL DEFAULT 1,

                xp INTEGER NOT NULL DEFAULT 0,

                xp_required INTEGER NOT NULL DEFAULT 100,

                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_statistics (

                character_id INTEGER PRIMARY KEY,

                strength INTEGER NOT NULL DEFAULT 1,

                constitution INTEGER NOT NULL DEFAULT 1,

                speed INTEGER NOT NULL DEFAULT 1,

                intelligence INTEGER NOT NULL DEFAULT 1,

                perception INTEGER NOT NULL DEFAULT 1,

                willpower INTEGER NOT NULL DEFAULT 1,

                luck INTEGER NOT NULL DEFAULT 1,

                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_resources (

                character_id INTEGER PRIMARY KEY,

                hp INTEGER NOT NULL DEFAULT 1,

                max_hp INTEGER NOT NULL DEFAULT 1,

                stamina INTEGER NOT NULL DEFAULT 1,

                max_stamina INTEGER NOT NULL DEFAULT 1,

                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL UNIQUE,

                description TEXT NOT NULL DEFAULT '',

                category TEXT NOT NULL DEFAULT 'general'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_classes (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                character_id INTEGER NOT NULL,

                class_id INTEGER NOT NULL,

                level INTEGER NOT NULL DEFAULT 1,

                experience INTEGER NOT NULL DEFAULT 0,

                is_primary INTEGER NOT NULL DEFAULT 0,

                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (class_id)
                    REFERENCES classes(id)
                    ON DELETE CASCADE,

                UNIQUE (
                    character_id,
                    class_id
                )
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_traits (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                character_id INTEGER NOT NULL,

                name TEXT NOT NULL,

                description TEXT NOT NULL DEFAULT '',

                category TEXT NOT NULL DEFAULT 'personality',

                strength INTEGER NOT NULL DEFAULT 50,

                stability TEXT NOT NULL DEFAULT 'flexible',

                origin TEXT NOT NULL DEFAULT 'initial',

                reason TEXT NOT NULL DEFAULT '',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_psychology (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                character_id INTEGER NOT NULL,

                type TEXT NOT NULL,

                name TEXT NOT NULL,

                description TEXT NOT NULL DEFAULT '',

                strength INTEGER NOT NULL DEFAULT 50,

                stability TEXT NOT NULL DEFAULT 'flexible',

                origin TEXT NOT NULL DEFAULT 'initial',

                reason TEXT NOT NULL DEFAULT '',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_states (

                character_id INTEGER PRIMARY KEY,

                emotion TEXT NOT NULL DEFAULT '',

                thought TEXT NOT NULL DEFAULT '',

                intention TEXT NOT NULL DEFAULT '',

                goal TEXT NOT NULL DEFAULT '',

                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                character_id INTEGER NOT NULL,

                content TEXT NOT NULL,

                memory_type TEXT NOT NULL DEFAULT 'event',

                importance INTEGER NOT NULL DEFAULT 5,

                is_secret INTEGER NOT NULL DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                character_a_id INTEGER NOT NULL,

                character_b_id INTEGER NOT NULL,

                relationship_type TEXT NOT NULL DEFAULT 'unknown',

                trust INTEGER NOT NULL DEFAULT 0,

                affection INTEGER NOT NULL DEFAULT 0,

                respect INTEGER NOT NULL DEFAULT 0,

                hostility INTEGER NOT NULL DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (character_a_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (character_b_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE,

                UNIQUE (
                    character_a_id,
                    character_b_id
                )
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_relationships (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                character_a_id INTEGER NOT NULL,

                character_b_id INTEGER NOT NULL,

                relationship_type TEXT NOT NULL,

                biological INTEGER NOT NULL DEFAULT 1,

                confirmed INTEGER NOT NULL DEFAULT 1,

                FOREIGN KEY (character_a_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (character_b_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE,

                UNIQUE (
                    character_a_id,
                    character_b_id,
                    relationship_type
                )
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_presence (

                character_id INTEGER PRIMARY KEY,

                location_id INTEGER NOT NULL,

                presence_state TEXT NOT NULL DEFAULT 'present',

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (character_id)
                    REFERENCES characters(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (location_id)
                    REFERENCES locations(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS world_events (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                turn_number INTEGER NOT NULL,

                event_type TEXT NOT NULL,

                actor_id INTEGER,

                target_id INTEGER,

                location_id INTEGER,

                data_json TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (actor_id)
                    REFERENCES characters(id),

                FOREIGN KEY (target_id)
                    REFERENCES characters(id),

                FOREIGN KEY (location_id)
                    REFERENCES locations(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_events (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                turn_number INTEGER NOT NULL,

                player_input TEXT NOT NULL,

                narration TEXT NOT NULL,

                actions_json TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        indexes = [

            """
            CREATE INDEX IF NOT EXISTS
            idx_character_traits_character
            ON character_traits(character_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_character_psychology_character
            ON character_psychology(character_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_memories_character
            ON memories(character_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_relationships_character_a
            ON relationships(character_a_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_relationships_character_b
            ON relationships(character_b_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_family_character_a
            ON family_relationships(character_a_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_family_character_b
            ON family_relationships(character_b_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_character_classes_character
            ON character_classes(character_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_world_events_location
            ON world_events(location_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_game_events_turn
            ON game_events(turn_number)
            """
        ]

        for index in indexes:
            cursor.execute(index)

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def reset_database():

    # Assicura che tutte le tabelle esistano
    initialize_database()

    connection = get_connection()
    cursor = connection.cursor()

    try:

        tables = [

            "game_events",
            "world_events",
            "character_presence",
            "family_relationships",
            "relationships",
            "memories",
            "character_psychology",
            "character_traits",
            "character_classes",
            "classes",
            "character_resources",
            "character_statistics",
            "character_progression",
            "character_states",
            "characters",
            "location_connections",
            "locations"
        ]

        for table in tables:

            cursor.execute(
                f"DELETE FROM {table}"
            )

        cursor.execute(
            "DELETE FROM sqlite_sequence"
        )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def has_existing_game():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT COUNT(*)
            FROM characters
        """)

        return cursor.fetchone()[0] > 0

    finally:

        connection.close()


def delete_database():

    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()


if __name__ == "__main__":

    initialize_database()

    print("DATABASE CREATO CORRETTAMENTE")