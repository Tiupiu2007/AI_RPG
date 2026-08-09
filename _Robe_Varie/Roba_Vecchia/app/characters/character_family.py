from _Robe_Varie.Roba_Vecchia.app.database import get_connection


# =========================================================
# CONFIGURAZIONE
# =========================================================

FAMILY_RELATIONSHIP_TYPES = (
    "parent",
    "child",
    "sibling",
    "brother",
    "sister",
    "grandparent",
    "grandchild",
    "uncle",
    "aunt",
    "nephew",
    "niece",
    "cousin",
    "spouse",
    "partner",
    "adoptive_parent",
    "adoptive_child",
    "step_parent",
    "step_child",
    "other",
)


# =========================================================
# VALIDAZIONE
# =========================================================

def _validate_character_id(character_id):

    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    if character_id <= 0:
        raise ValueError(
            "character_id deve essere maggiore di 0."
        )


def _validate_relationship_id(relationship_id):

    if not isinstance(relationship_id, int):
        raise ValueError(
            "relationship_id deve essere un intero."
        )

    if relationship_id <= 0:
        raise ValueError(
            "relationship_id deve essere maggiore di 0."
        )


def _validate_relationship_type(relationship_type):

    if not isinstance(relationship_type, str):
        raise ValueError(
            "relationship_type deve essere una stringa."
        )

    relationship_type = relationship_type.strip().lower()

    if not relationship_type:
        raise ValueError(
            "relationship_type non può essere vuoto."
        )

    if relationship_type not in FAMILY_RELATIONSHIP_TYPES:
        raise ValueError(
            f"Tipo di relazione familiare non valido: "
            f"{relationship_type}"
        )

    return relationship_type


def _validate_boolean(value, field_name):

    if not isinstance(value, bool):
        raise ValueError(
            f"{field_name} deve essere un booleano."
        )


# =========================================================
# CREAZIONE
# =========================================================

def create_family_relationship(
    character_a_id,
    character_b_id,
    relationship_type,
    biological=False,
    confirmed=False
):
    """
    Crea una relazione familiare tra due personaggi.

    Ritorna:
        int: ID della relazione creata.
    """

    _validate_character_id(character_a_id)
    _validate_character_id(character_b_id)

    if character_a_id == character_b_id:
        raise ValueError(
            "Un personaggio non può essere parente di se stesso."
        )

    relationship_type = _validate_relationship_type(
        relationship_type
    )

    _validate_boolean(
        biological,
        "biological"
    )

    _validate_boolean(
        confirmed,
        "confirmed"
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # Controllo personaggio A
        cursor.execute("""
            SELECT id
            FROM characters
            WHERE id = ?
        """, (
            character_a_id,
        ))

        if cursor.fetchone() is None:
            raise ValueError(
                "Personaggio A non trovato."
            )

        # Controllo personaggio B
        cursor.execute("""
            SELECT id
            FROM characters
            WHERE id = ?
        """, (
            character_b_id,
        ))

        if cursor.fetchone() is None:
            raise ValueError(
                "Personaggio B non trovato."
            )

        # Controllo duplicato
        cursor.execute("""
            SELECT id
            FROM family_relationships
            WHERE character_a_id = ?
              AND character_b_id = ?
              AND relationship_type = ?
        """, (
            character_a_id,
            character_b_id,
            relationship_type
        ))

        if cursor.fetchone() is not None:
            raise ValueError(
                "La relazione familiare esiste già."
            )

        # Inserimento
        cursor.execute("""
            INSERT INTO family_relationships (
                character_a_id,
                character_b_id,
                relationship_type,
                biological,
                confirmed
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            character_a_id,
            character_b_id,
            relationship_type,
            int(biological),
            int(confirmed)
        ))

        relationship_id = cursor.lastrowid

        connection.commit()

        return relationship_id

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# LETTURA
# =========================================================

def get_family_relationship(relationship_id):
    """
    Recupera una relazione familiare tramite ID.

    Ritorna:
        dict | None
    """

    _validate_relationship_id(
        relationship_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                character_a_id,
                character_b_id,
                relationship_type,
                biological,
                confirmed
            FROM family_relationships
            WHERE id = ?
        """, (
            relationship_id,
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "character_a_id": row["character_a_id"],
            "character_b_id": row["character_b_id"],
            "relationship_type": row["relationship_type"],
            "biological": bool(row["biological"]),
            "confirmed": bool(row["confirmed"])
        }

    finally:

        connection.close()


# =========================================================
# FAMIGLIA PERSONAGGIO
# =========================================================

def get_character_family(character_id):
    """
    Recupera tutte le relazioni familiari
    di un personaggio.

    Il personaggio può trovarsi sia come
    character_a_id sia come character_b_id.
    """

    _validate_character_id(
        character_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                character_a_id,
                character_b_id,
                relationship_type,
                biological,
                confirmed
            FROM family_relationships
            WHERE character_a_id = ?
               OR character_b_id = ?
            ORDER BY id ASC
        """, (
            character_id,
            character_id
        ))

        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "character_a_id": row["character_a_id"],
                "character_b_id": row["character_b_id"],
                "relationship_type": row["relationship_type"],
                "biological": bool(row["biological"]),
                "confirmed": bool(row["confirmed"])
            }
            for row in rows
        ]

    finally:

        connection.close()


# =========================================================
# AGGIORNAMENTO
# =========================================================

def update_family_relationship(
    relationship_id,
    relationship_type=None,
    biological=None,
    confirmed=None
):
    """
    Aggiorna una relazione familiare.

    I parametri None non vengono modificati.

    Ritorna:
        bool
    """

    _validate_relationship_id(
        relationship_id
    )

    fields = []
    values = []

    if relationship_type is not None:

        relationship_type = _validate_relationship_type(
            relationship_type
        )

        fields.append(
            "relationship_type = ?"
        )

        values.append(
            relationship_type
        )

    if biological is not None:

        _validate_boolean(
            biological,
            "biological"
        )

        fields.append(
            "biological = ?"
        )

        values.append(
            int(biological)
        )

    if confirmed is not None:

        _validate_boolean(
            confirmed,
            "confirmed"
        )

        fields.append(
            "confirmed = ?"
        )

        values.append(
            int(confirmed)
        )

    if not fields:
        return False

    values.append(
        relationship_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            UPDATE family_relationships
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Relazione familiare non trovata."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# ELIMINAZIONE
# =========================================================

def delete_family_relationship(
    relationship_id
):
    """
    Elimina una relazione familiare.

    Ritorna:
        bool
    """

    _validate_relationship_id(
        relationship_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM family_relationships
            WHERE id = ?
        """, (
            relationship_id,
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                "Relazione familiare non trovata."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()