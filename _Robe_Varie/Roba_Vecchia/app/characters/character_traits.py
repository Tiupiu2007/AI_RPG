from _Robe_Varie.Roba_Vecchia.app.database import get_connection


TRAIT_CATEGORIES = (
    "personality",
    "behavior",
    "physical",
    "social",
    "mental",
    "combat",
    "racial",
    "custom"
)

STABILITY_TYPES = (
    "fundamental",
    "strong",
    "flexible",
    "temporary"
)

ORIGINS = (
    "initial",
    "experience",
    "event",
    "relationship",
    "training",
    "acquired",
    "unknown"
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


def _validate_category(category):
    if not isinstance(category, str):
        raise ValueError(
            "category deve essere una stringa."
        )

    category = category.strip().lower()

    if category not in TRAIT_CATEGORIES:
        raise ValueError(
            f"Categoria del tratto non valida: {category}"
        )

    return category


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


def _validate_origin(origin):
    if not isinstance(origin, str):
        raise ValueError(
            "origin deve essere una stringa."
        )

    origin = origin.strip().lower()

    if origin not in ORIGINS:
        raise ValueError(
            f"Origine non valida: {origin}"
        )

    return origin


def _validate_strength(strength):
    if not isinstance(strength, int):
        raise ValueError(
            "strength deve essere un intero."
        )

    if not MIN_STRENGTH <= strength <= MAX_STRENGTH:
        raise ValueError(
            "strength deve essere compresa tra 0 e 100."
        )


def create_character_trait(
    character_id,
    name,
    description="",
    category="personality",
    strength=50,
    stability="flexible",
    origin="initial",
    reason=""
):
    _validate_character_id(character_id)

    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "name deve essere una stringa non vuota."
        )

    if not isinstance(description, str):
        raise ValueError(
            "description deve essere una stringa."
        )

    category = _validate_category(category)
    stability = _validate_stability(stability)
    origin = _validate_origin(origin)

    _validate_strength(strength)

    if not isinstance(reason, str):
        raise ValueError(
            "reason deve essere una stringa."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO character_traits (
                character_id,
                name,
                description,
                category,
                strength,
                stability,
                origin,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            character_id,
            name.strip(),
            description,
            category,
            strength,
            stability,
            origin,
            reason
        ))

        trait_id = cursor.lastrowid

        connection.commit()

        return trait_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_character_trait(trait_id):
    if not isinstance(trait_id, int):
        raise ValueError(
            "trait_id deve essere un intero."
        )

    if trait_id <= 0:
        raise ValueError(
            "trait_id deve essere maggiore di 0."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                character_id,
                name,
                description,
                category,
                strength,
                stability,
                origin,
                reason,
                created_at,
                updated_at
            FROM character_traits
            WHERE id = ?
        """, (
            trait_id,
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def get_character_traits(character_id):
    _validate_character_id(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                character_id,
                name,
                description,
                category,
                strength,
                stability,
                origin,
                reason,
                created_at,
                updated_at
            FROM character_traits
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


def get_character_traits_by_category(
    character_id,
    category
):
    _validate_character_id(character_id)

    category = _validate_category(category)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                character_id,
                name,
                description,
                category,
                strength,
                stability,
                origin,
                reason,
                created_at,
                updated_at
            FROM character_traits
            WHERE character_id = ?
              AND category = ?
            ORDER BY strength DESC, id ASC
        """, (
            character_id,
            category
        ))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def find_character_trait(
    character_id,
    name
):
    _validate_character_id(character_id)

    if not isinstance(name, str) or not name.strip():
        return None

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                character_id,
                name,
                description,
                category,
                strength,
                stability,
                origin,
                reason,
                created_at,
                updated_at
            FROM character_traits
            WHERE character_id = ?
              AND LOWER(name) = LOWER(?)
            LIMIT 1
        """, (
            character_id,
            name.strip()
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def update_character_trait(
    trait_id,
    name=None,
    description=None,
    category=None,
    strength=None,
    stability=None,
    origin=None,
    reason=None
):
    if not isinstance(trait_id, int):
        raise ValueError(
            "trait_id deve essere un intero."
        )

    if trait_id <= 0:
        raise ValueError(
            "trait_id deve essere maggiore di 0."
        )

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

        fields.append("category = ?")
        values.append(
            _validate_category(category)
        )

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

        fields.append("origin = ?")
        values.append(
            _validate_origin(origin)
        )

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

    values.append(trait_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            f"""
            UPDATE character_traits
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Tratto non trovato."
            )

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def modify_character_trait_strength(
    trait_id,
    amount
):
    if not isinstance(amount, int):
        raise ValueError(
            "amount deve essere un intero."
        )

    trait = get_character_trait(trait_id)

    if trait is None:
        raise ValueError(
            "Tratto non trovato."
        )

    new_strength = max(
        MIN_STRENGTH,
        min(
            MAX_STRENGTH,
            trait["strength"] + amount
        )
    )

    update_character_trait(
        trait_id=trait_id,
        strength=new_strength
    )

    return new_strength


def delete_character_trait(trait_id):
    if not isinstance(trait_id, int):
        raise ValueError(
            "trait_id deve essere un intero."
        )

    if trait_id <= 0:
        raise ValueError(
            "trait_id deve essere maggiore di 0."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM character_traits
            WHERE id = ?
        """, (
            trait_id,
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                "Tratto non trovato."
            )

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()