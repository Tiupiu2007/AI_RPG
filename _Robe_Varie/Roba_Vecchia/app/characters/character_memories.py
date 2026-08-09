from _Robe_Varie.Roba_Vecchia.app.database import get_connection


# =========================================================
# CONFIGURAZIONE
# =========================================================

MEMORY_TYPES = (
    "event",
    "fact",
    "person",
    "place",
    "secret",
    "knowledge",
    "experience"
)

MIN_IMPORTANCE = 1
MAX_IMPORTANCE = 10


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


def _validate_memory_id(memory_id):

    if not isinstance(memory_id, int):
        raise ValueError(
            "memory_id deve essere un intero."
        )

    if memory_id <= 0:
        raise ValueError(
            "memory_id deve essere maggiore di 0."
        )


def _validate_memory_type(memory_type):

    if not isinstance(memory_type, str):
        raise ValueError(
            "memory_type deve essere una stringa."
        )

    memory_type = memory_type.strip().lower()

    if memory_type not in MEMORY_TYPES:
        raise ValueError(
            f"Tipo di memoria non valido: {memory_type}"
        )

    return memory_type


def _validate_importance(importance):

    if not isinstance(importance, int):
        raise ValueError(
            "importance deve essere un intero."
        )

    if not MIN_IMPORTANCE <= importance <= MAX_IMPORTANCE:
        raise ValueError(
            f"importance deve essere compresa tra "
            f"{MIN_IMPORTANCE} e {MAX_IMPORTANCE}."
        )


# =========================================================
# CREAZIONE MEMORIA
# =========================================================

def create_memory(
    character_id,
    content,
    memory_type="event",
    importance=5,
    is_secret=False
):
    """
    Crea una nuova memoria del personaggio.

    Ritorna:
        int: ID della memoria creata.
    """

    _validate_character_id(character_id)

    if not isinstance(content, str) or not content.strip():
        raise ValueError(
            "content deve essere una stringa non vuota."
        )

    memory_type = _validate_memory_type(memory_type)

    _validate_importance(importance)

    if not isinstance(is_secret, bool):
        raise ValueError(
            "is_secret deve essere un booleano."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

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

        cursor.execute("""
            INSERT INTO memories (
                character_id,
                content,
                memory_type,
                importance,
                is_secret
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            character_id,
            content.strip(),
            memory_type,
            importance,
            int(is_secret)
        ))

        memory_id = cursor.lastrowid

        connection.commit()

        return memory_id

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# LETTURA MEMORIA
# =========================================================

def get_memory(memory_id):
    """
    Recupera una memoria tramite ID.

    Ritorna:
        dict | None
    """

    _validate_memory_id(memory_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                character_id,
                content,
                memory_type,
                importance,
                is_secret,
                created_at
            FROM memories
            WHERE id = ?
        """, (
            memory_id,
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "character_id": row["character_id"],
            "content": row["content"],
            "memory_type": row["memory_type"],
            "importance": row["importance"],
            "is_secret": bool(row["is_secret"]),
            "created_at": row["created_at"]
        }

    finally:

        connection.close()


# =========================================================
# MEMORIE DEL PERSONAGGIO
# =========================================================

def get_character_memories(
    character_id,
    include_secrets=True
):
    """
    Recupera tutte le memorie di un personaggio.

    Le memorie vengono ordinate per importanza
    decrescente e successivamente per ID.
    """

    _validate_character_id(character_id)

    if not isinstance(include_secrets, bool):
        raise ValueError(
            "include_secrets deve essere un booleano."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        if include_secrets:

            cursor.execute("""
                SELECT
                    id,
                    character_id,
                    content,
                    memory_type,
                    importance,
                    is_secret,
                    created_at
                FROM memories
                WHERE character_id = ?
                ORDER BY importance DESC, id DESC
            """, (
                character_id,
            ))

        else:

            cursor.execute("""
                SELECT
                    id,
                    character_id,
                    content,
                    memory_type,
                    importance,
                    is_secret,
                    created_at
                FROM memories
                WHERE character_id = ?
                AND is_secret = 0
                ORDER BY importance DESC, id DESC
            """, (
                character_id,
            ))

        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "character_id": row["character_id"],
                "content": row["content"],
                "memory_type": row["memory_type"],
                "importance": row["importance"],
                "is_secret": bool(row["is_secret"]),
                "created_at": row["created_at"]
            }
            for row in rows
        ]

    finally:

        connection.close()


# =========================================================
# MEMORIE IMPORTANTI
# =========================================================

def get_important_character_memories(
    character_id,
    minimum_importance=7,
    include_secrets=True
):
    """
    Recupera solamente le memorie considerate importanti.
    """

    _validate_character_id(character_id)

    _validate_importance(minimum_importance)

    return [
        memory
        for memory in get_character_memories(
            character_id,
            include_secrets=include_secrets
        )
        if memory["importance"] >= minimum_importance
    ]


# =========================================================
# AGGIORNAMENTO MEMORIA
# =========================================================

def update_memory(
    memory_id,
    content=None,
    memory_type=None,
    importance=None,
    is_secret=None
):
    """
    Aggiorna una memoria.

    I parametri None non vengono modificati.

    Ritorna:
        bool
    """

    _validate_memory_id(memory_id)

    fields = []
    values = []

    # -----------------------------------------------------
    # CONTENUTO
    # -----------------------------------------------------

    if content is not None:

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                "content deve essere una stringa non vuota."
            )

        fields.append("content = ?")
        values.append(content.strip())

    # -----------------------------------------------------
    # TIPO
    # -----------------------------------------------------

    if memory_type is not None:

        memory_type = _validate_memory_type(
            memory_type
        )

        fields.append("memory_type = ?")
        values.append(memory_type)

    # -----------------------------------------------------
    # IMPORTANZA
    # -----------------------------------------------------

    if importance is not None:

        _validate_importance(importance)

        fields.append("importance = ?")
        values.append(importance)

    # -----------------------------------------------------
    # SEGRETEZZA
    # -----------------------------------------------------

    if is_secret is not None:

        if not isinstance(is_secret, bool):
            raise ValueError(
                "is_secret deve essere un booleano."
            )

        fields.append("is_secret = ?")
        values.append(int(is_secret))

    # -----------------------------------------------------
    # NIENTE DA MODIFICARE
    # -----------------------------------------------------

    if not fields:
        return False

    values.append(memory_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            UPDATE memories
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Memoria non trovata."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# ELIMINAZIONE MEMORIA
# =========================================================

def delete_memory(memory_id):
    """
    Elimina una memoria dal database.

    Ritorna:
        bool
    """

    _validate_memory_id(memory_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM memories
            WHERE id = ?
        """, (
            memory_id,
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                "Memoria non trovata."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


