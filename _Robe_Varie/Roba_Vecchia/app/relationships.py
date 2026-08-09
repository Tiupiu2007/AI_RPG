from _Robe_Varie.Roba_Vecchia.app.database import get_connection


MIN_RELATIONSHIP_VALUE = -100
MAX_RELATIONSHIP_VALUE = 100


# =========================================================
# LIMITAZIONE VALORE
# =========================================================

def clamp_relationship_value(value):
    """
    Mantiene un valore di relazione tra -100 e +100.
    """

    return max(
        MIN_RELATIONSHIP_VALUE,
        min(MAX_RELATIONSHIP_VALUE, value)
    )


# =========================================================
# CREAZIONE RELAZIONE
# =========================================================

def create_relationship(
    character_a_id,
    character_b_id,
    trust=0,
    affection=0,
    respect=0,
    hostility=0
):
    """
    Crea una relazione tra due personaggi.

    I valori iniziali sono compresi tra -100 e +100.
    """

    if character_a_id == character_b_id:
        raise ValueError(
            "Un personaggio non può avere una relazione con se stesso."
        )

    trust = clamp_relationship_value(trust)
    affection = clamp_relationship_value(affection)
    respect = clamp_relationship_value(respect)
    hostility = clamp_relationship_value(hostility)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO relationships (
                character_a_id,
                character_b_id,
                trust,
                affection,
                respect,
                hostility
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            character_a_id,
            character_b_id,
            trust,
            affection,
            respect,
            hostility
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
# LETTURA RELAZIONE
# =========================================================

def get_relationship(
    character_a_id,
    character_b_id
):
    """
    Recupera una relazione tra due personaggi.

    La ricerca funziona in entrambe le direzioni:
    A -> B
    B -> A

    Ritorna:
        sqlite3.Row | None
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                character_a_id,
                character_b_id,
                trust,
                affection,
                respect,
                hostility
            FROM relationships
            WHERE
                (
                    character_a_id = ?
                    AND character_b_id = ?
                )
                OR
                (
                    character_a_id = ?
                    AND character_b_id = ?
                )
            LIMIT 1
        """, (
            character_a_id,
            character_b_id,
            character_b_id,
            character_a_id
        ))

        return cursor.fetchone()

    finally:
        connection.close()


# =========================================================
# AGGIORNAMENTO ASSOLUTO
# =========================================================

def update_relationship(
    character_a_id,
    character_b_id,
    trust=None,
    affection=None,
    respect=None,
    hostility=None
):
    """
    Imposta valori assoluti della relazione.

    None significa mantenere il valore attuale.
    """

    current = get_relationship(
        character_a_id,
        character_b_id
    )

    if current is None:
        raise ValueError(
            "Relazione non trovata."
        )

    trust = (
        current["trust"]
        if trust is None
        else clamp_relationship_value(trust)
    )

    affection = (
        current["affection"]
        if affection is None
        else clamp_relationship_value(affection)
    )

    respect = (
        current["respect"]
        if respect is None
        else clamp_relationship_value(respect)
    )

    hostility = (
        current["hostility"]
        if hostility is None
        else clamp_relationship_value(hostility)
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            UPDATE relationships
            SET
                trust = ?,
                affection = ?,
                respect = ?,
                hostility = ?
            WHERE id = ?
        """, (
            trust,
            affection,
            respect,
            hostility,
            current["id"]
        ))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return get_relationship(
        character_a_id,
        character_b_id
    )


# =========================================================
# MODIFICA RELAZIONE CON DELTA
# =========================================================

def change_relationship(
    character_a_id,
    character_b_id,
    trust=0,
    affection=0,
    respect=0,
    hostility=0
):
    """
    Modifica la relazione usando variazioni relative.

    Esempio:

        trust attuale = 40
        trust = 5

        nuovo trust = 45
    """

    # -----------------------------------------------------
    # VALIDAZIONE DELLE VARIAZIONI
    # -----------------------------------------------------

    values = {
        "trust": trust,
        "affection": affection,
        "respect": respect,
        "hostility": hostility
    }

    for name, value in values.items():

        if not isinstance(value, int):
            raise ValueError(
                f"{name} deve essere un intero."
            )

        if value < -30 or value > 30:
            raise ValueError(
                f"{name} deve essere compreso "
                "tra -30 e 30."
            )

    # -----------------------------------------------------
    # RELAZIONE ATTUALE
    # -----------------------------------------------------

    current = get_relationship(
        character_a_id,
        character_b_id
    )

    if current is None:
        raise ValueError(
            "Relazione non trovata."
        )

    # -----------------------------------------------------
    # NUOVI VALORI
    # -----------------------------------------------------

    new_trust = clamp_relationship_value(
        current["trust"] + trust
    )

    new_affection = clamp_relationship_value(
        current["affection"] + affection
    )

    new_respect = clamp_relationship_value(
        current["respect"] + respect
    )

    new_hostility = clamp_relationship_value(
        current["hostility"] + hostility
    )

    # -----------------------------------------------------
    # AGGIORNAMENTO
    # -----------------------------------------------------

    return update_relationship(
        character_a_id=character_a_id,
        character_b_id=character_b_id,
        trust=new_trust,
        affection=new_affection,
        respect=new_respect,
        hostility=new_hostility
    )