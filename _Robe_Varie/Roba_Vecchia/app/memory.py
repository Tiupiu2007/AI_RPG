from _Robe_Varie.Roba_Vecchia.app.database import get_connection


# =========================================================
# CREAZIONE MEMORIA
# =========================================================

def create_memory(
    character_id,
    content,
    memory_type,
    importance,
    is_secret=False
):
    """
    Crea una memoria persistente per un personaggio.

    importance:
        Valore da 1 a 10.

    Ritorna:
        int: ID della memoria creata.
    """

    # =====================================================
    # VALIDAZIONE
    # =====================================================

    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    if not isinstance(content, str):
        raise ValueError(
            "content deve essere una stringa."
        )

    content = content.strip()

    if not content:
        raise ValueError(
            "content non può essere vuoto."
        )

    if not isinstance(memory_type, str):
        raise ValueError(
            "memory_type deve essere una stringa."
        )

    memory_type = memory_type.strip()

    if not memory_type:
        raise ValueError(
            "memory_type non può essere vuoto."
        )

    if not isinstance(importance, int):
        raise ValueError(
            "importance deve essere un intero."
        )

    if not 1 <= importance <= 10:
        raise ValueError(
            "importance deve essere compreso tra 1 e 10."
        )

    if not isinstance(is_secret, bool):
        raise ValueError(
            "is_secret deve essere True oppure False."
        )

    # =====================================================
    # LIMITE MEMORIA
    # =====================================================

    if len(content) > 500:
        raise ValueError(
            "La memoria non può superare 500 caratteri."
        )

    # =====================================================
    # CONTROLLO DUPLICATO
    # =====================================================

    if memory_exists(
        character_id=character_id,
        content=content
    ):
        return None

    # =====================================================
    # DATABASE
    # =====================================================

    connection = get_connection()
    cursor = connection.cursor()

    try:

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
            content,
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
# OTTIENI MEMORIE
# =========================================================

def get_character_memories(
    character_id,
    limit=None
):
    """
    Recupera le memorie di un personaggio.

    Ordine:

    1. importanza maggiore
    2. memoria più recente

    Ritorna:
        list[sqlite3.Row]
    """

    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        if limit is None:

            cursor.execute("""
                SELECT
                    id,
                    character_id,
                    content,
                    memory_type,
                    importance,
                    is_secret
                FROM memories
                WHERE character_id = ?
                ORDER BY importance DESC, id DESC
            """, (
                character_id,
            ))

        else:

            if not isinstance(limit, int):
                raise ValueError(
                    "limit deve essere un intero oppure None."
                )

            if limit <= 0:
                raise ValueError(
                    "limit deve essere maggiore di 0."
                )

            cursor.execute("""
                SELECT
                    id,
                    character_id,
                    content,
                    memory_type,
                    importance,
                    is_secret
                FROM memories
                WHERE character_id = ?
                ORDER BY importance DESC, id DESC
                LIMIT ?
            """, (
                character_id,
                limit
            ))

        return cursor.fetchall()

    finally:

        connection.close()


# =========================================================
# OTTIENI MEMORIE IMPORTANTI
# =========================================================

def get_important_memories(
    character_id,
    minimum_importance=7
):
    """
    Recupera solamente le memorie importanti.

    Di default:
        importance >= 7

    Ritorna:
        list[sqlite3.Row]
    """

    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    if not isinstance(minimum_importance, int):
        raise ValueError(
            "minimum_importance deve essere un intero."
        )

    if not 1 <= minimum_importance <= 10:
        raise ValueError(
            "minimum_importance deve essere compreso "
            "tra 1 e 10."
        )

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
                is_secret
            FROM memories
            WHERE character_id = ?
              AND importance >= ?
            ORDER BY importance DESC, id DESC
        """, (
            character_id,
            minimum_importance
        ))

        return cursor.fetchall()

    finally:

        connection.close()


# =========================================================
# VERIFICA MEMORIA DUPLICATA
# =========================================================

def memory_exists(
    character_id,
    content
):
    """
    Controlla se il personaggio possiede già
    una memoria con lo stesso contenuto.

    Ritorna:
        True / False
    """

    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    if not isinstance(content, str):
        raise ValueError(
            "content deve essere una stringa."
        )

    content = content.strip()

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM memories
            WHERE character_id = ?
              AND content = ?
            LIMIT 1
        """, (
            character_id,
            content
        ))

        row = cursor.fetchone()

        return row is not None

    finally:

        connection.close()