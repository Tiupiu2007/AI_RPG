from _Robe_Varie.Roba_Vecchia.app.database import get_connection


PSYCHOLOGY_TYPES = (
    "fear",
    "desire",
    "value",
    "belief",
    "trauma",
    "motivation",
    "insecurity",
    "attachment",
    "aversion",
    "ideal"
)

STABILITY_TYPES = (
    "fundamental",
    "strong",
    "flexible",
    "temporary"
)

MIN_STRENGTH = 0
MAX_STRENGTH = 100


def _validate_character_id(character_id):
    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    if character_id <= 0:
        raise ValueError(
            "character_id deve essere maggiore di 0."
        )


def _validate_type(value):
    if not isinstance(value, str):
        raise ValueError(
            "type deve essere una stringa."
        )

    value = value.strip().lower()

    if value not in PSYCHOLOGY_TYPES:
        raise ValueError(
            f"Tipo psicologico non valido: {value}"
        )

    return value


def _validate_stability(stability):
    if not isinstance(stability, str):
        raise ValueError(
            "stability deve essere una stringa."
        )

    stability = stability.strip().lower()

    if stability not in STABILITY_TYPES:
        raise ValueError(
            f"Stabilità non valida: {stability}"
        )

    return stability


def _validate_strength(strength):
    if not isinstance(strength, int):
        raise ValueError(
            "strength deve essere un intero."
        )

    if not MIN_STRENGTH <= strength <= MAX_STRENGTH:
        raise ValueError(
            "strength deve essere compresa tra 0 e 100."
        )


def create_character_psychology(
    character_id,
    type,
    name,
    description="",
    strength=50,
    stability="flexible",
    origin="initial",
    reason=""
):
    _validate_character_id(character_id)

    type = _validate_type(type)
    stability = _validate_stability(stability)
    _validate_strength(strength)

    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "name deve essere una stringa non vuota."
        )

    if not isinstance(description, str):
        raise ValueError(
            "description deve essere una stringa."
        )

    if not isinstance(origin, str):
        raise ValueError(
            "origin deve essere una stringa."
        )

    if not isinstance(reason, str):
        raise ValueError(
            "reason deve essere una stringa."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO character_psychology (
                character_id,
                type,
                name,
                description,
                strength,
                stability,
                origin,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            character_id,
            type,
            name.strip(),
            description,
            strength,
            stability,
            origin,
            reason
        ))

        psychology_id = cursor.lastrowid

        connection.commit()

        return psychology_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_character_psychology(psychology_id):
    if not isinstance(psychology_id, int):
        raise ValueError(
            "psychology_id deve essere un intero."
        )

    if psychology_id <= 0:
        raise ValueError(
            "psychology_id deve essere maggiore di 0."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                character_id,
                type,
                name,
                description,
                strength,
                stability,
                origin,
                reason,
                created_at,
                updated_at
            FROM character_psychology
            WHERE id = ?
        """, (
            psychology_id,
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def get_character_psychologies(character_id):
    _validate_character_id(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                character_id,
                type,
                name,
                description,
                strength,
                stability,
                origin,
                reason,
                created_at,
                updated_at
            FROM character_psychology
            WHERE character_id = ?
            ORDER BY strength DESC, id ASC
        """, (
            character_id,
        ))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def get_character_psychologies_by_type(
    character_id,
    type
):
    _validate_character_id(character_id)

    type = _validate_type(type)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                character_id,
                type,
                name,
                description,
                strength,
                stability,
                origin,
                reason,
                created_at,
                updated_at
            FROM character_psychology
            WHERE character_id = ?
              AND type = ?
            ORDER BY strength DESC, id ASC
        """, (
            character_id,
            type
        ))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def update_character_psychology(
    psychology_id,
    type=None,
    name=None,
    description=None,
    strength=None,
    stability=None,
    origin=None,
    reason=None
):
    if not isinstance(psychology_id, int):
        raise ValueError(
            "psychology_id deve essere un intero."
        )

    if psychology_id <= 0:
        raise ValueError(
            "psychology_id deve essere maggiore di 0."
        )

    fields = []
    values = []

    if type is not None:
        fields.append("type = ?")
        values.append(_validate_type(type))

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

    if strength is not None:

        _validate_strength(strength)

        fields.append("strength = ?")
        values.append(strength)

    if stability is not None:

        fields.append("stability = ?")
        values.append(
            _validate_stability(stability)
        )

    if origin is not None:

        if not isinstance(origin, str):
            raise ValueError(
                "origin deve essere una stringa."
            )

        fields.append("origin = ?")
        values.append(origin)

    if reason is not None:

        if not isinstance(reason, str):
            raise ValueError(
                "reason deve essere una stringa."
            )

        fields.append("reason = ?")
        values.append(reason)

    if not fields:
        return False

    fields.append(
        "updated_at = CURRENT_TIMESTAMP"
    )

    values.append(psychology_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            f"""
            UPDATE character_psychology
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Elemento psicologico non trovato."
            )

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def modify_character_psychology_strength(
    psychology_id,
    amount
):
    if not isinstance(amount, int):
        raise ValueError(
            "amount deve essere un intero."
        )

    current = get_character_psychology(
        psychology_id
    )

    if current is None:
        raise ValueError(
            "Elemento psicologico non trovato."
        )

    new_strength = max(
        MIN_STRENGTH,
        min(
            MAX_STRENGTH,
            current["strength"] + amount
        )
    )

    update_character_psychology(
        psychology_id=psychology_id,
        strength=new_strength
    )

    return new_strength


def delete_character_psychology(psychology_id):
    if not isinstance(psychology_id, int):
        raise ValueError(
            "psychology_id deve essere un intero."
        )

    if psychology_id <= 0:
        raise ValueError(
            "psychology_id deve essere maggiore di 0."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM character_psychology
            WHERE id = ?
        """, (
            psychology_id,
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                "Elemento psicologico non trovato."
            )

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()