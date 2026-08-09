from _Robe_Varie.Roba_Vecchia.app.database import get_connection


MAX_CHARACTER_CLASSES = 999
MAX_CLASS_LEVEL = 999


def _validate_character_id(character_id):

    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    if character_id <= 0:
        raise ValueError(
            "character_id deve essere maggiore di 0."
        )


def _validate_class_id(class_id):

    if not isinstance(class_id, int):
        raise ValueError(
            "class_id deve essere un intero."
        )

    if class_id <= 0:
        raise ValueError(
            "class_id deve essere maggiore di 0."
        )


def _validate_level(level):

    if not isinstance(level, int):
        raise ValueError(
            "level deve essere un intero."
        )

    if level < 1 or level > MAX_CLASS_LEVEL:
        raise ValueError(
            f"level deve essere compreso tra 1 e {MAX_CLASS_LEVEL}."
        )


def _validate_experience(experience):

    if not isinstance(experience, int):
        raise ValueError(
            "experience deve essere un intero."
        )

    if experience < 0:
        raise ValueError(
            "experience non può essere negativa."
        )


def create_class(
    name,
    description="",
    category="general"
):

    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "Il nome della classe è obbligatorio."
        )

    if not isinstance(description, str):
        raise ValueError(
            "description deve essere una stringa."
        )

    if not isinstance(category, str) or not category.strip():
        raise ValueError(
            "category deve essere una stringa non vuota."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT COUNT(*)
            FROM classes
        """)

        count = cursor.fetchone()[0]

        if count >= MAX_CHARACTER_CLASSES:
            raise ValueError(
                "È stato raggiunto il numero massimo "
                "di classi disponibili."
            )

        cursor.execute("""
            INSERT INTO classes (
                name,
                description,
                category
            )
            VALUES (?, ?, ?)
        """, (
            name.strip(),
            description,
            category.strip()
        ))

        class_id = cursor.lastrowid

        connection.commit()

        return class_id

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_class(class_id):

    _validate_class_id(class_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                description,
                category
            FROM classes
            WHERE id = ?
        """, (
            class_id,
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:

        connection.close()


def get_all_classes():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                description,
                category
            FROM classes
            ORDER BY name ASC
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:

        connection.close()


def find_class(name):

    if not isinstance(name, str) or not name.strip():
        return None

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                description,
                category
            FROM classes
            WHERE LOWER(name) = LOWER(?)
            LIMIT 1
        """, (
            name.strip(),
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:

        connection.close()


def update_class(
    class_id,
    name=None,
    description=None,
    category=None
):

    _validate_class_id(class_id)

    fields = []
    values = []

    if name is not None:

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "name deve essere una stringa non vuota."
            )

        fields.append("name = ?")
        values.append(name.strip())

    if description is not None:

        if not isinstance(description, str):
            raise ValueError(
                "description deve essere una stringa."
            )

        fields.append("description = ?")
        values.append(description)

    if category is not None:

        if not isinstance(category, str) or not category.strip():
            raise ValueError(
                "category deve essere una stringa non vuota."
            )

        fields.append("category = ?")
        values.append(category.strip())

    if not fields:
        return False

    values.append(class_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            UPDATE classes
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Classe non trovata."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def delete_class(class_id):

    _validate_class_id(class_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT COUNT(*)
            FROM character_classes
            WHERE class_id = ?
        """, (
            class_id,
        ))

        if cursor.fetchone()[0] > 0:
            raise ValueError(
                "La classe è ancora assegnata a uno o più personaggi."
            )

        cursor.execute("""
            DELETE FROM classes
            WHERE id = ?
        """, (
            class_id,
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                "Classe non trovata."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def add_character_class(
    character_id,
    class_id,
    level=1,
    experience=0,
    is_primary=False
):

    _validate_character_id(character_id)
    _validate_class_id(class_id)
    _validate_level(level)
    _validate_experience(experience)

    if not isinstance(is_primary, bool):
        raise ValueError(
            "is_primary deve essere un booleano."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM classes
            WHERE id = ?
        """, (
            class_id,
        ))

        if cursor.fetchone() is None:
            raise ValueError(
                "Classe non trovata."
            )

        cursor.execute("""
            SELECT id
            FROM characters
            WHERE id = ?
        """, (
            character_id,
        ))

        if cursor.fetchone() is None:
            raise ValueError(
                "Personaggio non trovato."
            )

        if is_primary:

            cursor.execute("""
                UPDATE character_classes
                SET is_primary = 0
                WHERE character_id = ?
            """, (
                character_id,
            ))

        cursor.execute("""
            INSERT INTO character_classes (
                character_id,
                class_id,
                level,
                experience,
                is_primary
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            character_id,
            class_id,
            level,
            experience,
            1 if is_primary else 0
        ))

        character_class_id = cursor.lastrowid

        connection.commit()

        return character_class_id

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def remove_character_class(
    character_id,
    class_id
):

    _validate_character_id(character_id)
    _validate_class_id(class_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM character_classes
            WHERE character_id = ?
            AND class_id = ?
        """, (
            character_id,
            class_id
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                "Il personaggio non possiede questa classe."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_character_classes(character_id):

    _validate_character_id(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                cc.id,
                cc.character_id,
                cc.class_id,
                c.name,
                c.description,
                c.category,
                cc.level,
                cc.experience,
                cc.is_primary
            FROM character_classes cc
            INNER JOIN classes c
                ON c.id = cc.class_id
            WHERE cc.character_id = ?
            ORDER BY cc.is_primary DESC, c.name ASC
        """, (
            character_id,
        ))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:

        connection.close()


def get_character_class(
    character_id,
    class_id
):

    _validate_character_id(character_id)
    _validate_class_id(class_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                cc.id,
                cc.character_id,
                cc.class_id,
                c.name,
                c.description,
                c.category,
                cc.level,
                cc.experience,
                cc.is_primary
            FROM character_classes cc
            INNER JOIN classes c
                ON c.id = cc.class_id
            WHERE cc.character_id = ?
            AND cc.class_id = ?
        """, (
            character_id,
            class_id
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:

        connection.close()


def set_primary_class(
    character_id,
    class_id
):

    _validate_character_id(character_id)
    _validate_class_id(class_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM character_classes
            WHERE character_id = ?
            AND class_id = ?
        """, (
            character_id,
            class_id
        ))

        if cursor.fetchone() is None:
            raise ValueError(
                "Il personaggio non possiede questa classe."
            )

        cursor.execute("""
            UPDATE character_classes
            SET is_primary = 0
            WHERE character_id = ?
        """, (
            character_id,
        ))

        cursor.execute("""
            UPDATE character_classes
            SET is_primary = 1
            WHERE character_id = ?
            AND class_id = ?
        """, (
            character_id,
            class_id
        ))

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def update_character_class(
    character_id,
    class_id,
    level=None,
    experience=None,
    is_primary=None
):

    _validate_character_id(character_id)
    _validate_class_id(class_id)

    fields = []
    values = []

    if level is not None:

        _validate_level(level)

        fields.append("level = ?")
        values.append(level)

    if experience is not None:

        _validate_experience(experience)

        fields.append("experience = ?")
        values.append(experience)

    if is_primary is not None:

        if not isinstance(is_primary, bool):
            raise ValueError(
                "is_primary deve essere un booleano."
            )

        fields.append("is_primary = ?")
        values.append(1 if is_primary else 0)

    if not fields:
        return False

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM character_classes
            WHERE character_id = ?
            AND class_id = ?
        """, (
            character_id,
            class_id
        ))

        if cursor.fetchone() is None:
            raise ValueError(
                "Il personaggio non possiede questa classe."
            )

        if is_primary is True:

            cursor.execute("""
                UPDATE character_classes
                SET is_primary = 0
                WHERE character_id = ?
            """, (
                character_id,
            ))

        values.extend([
            character_id,
            class_id
        ])

        cursor.execute(
            f"""
            UPDATE character_classes
            SET {", ".join(fields)}
            WHERE character_id = ?
            AND class_id = ?
            """,
            values
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Classe del personaggio non trovata."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()