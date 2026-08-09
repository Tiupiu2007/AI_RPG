from _Robe_Varie.Roba_Vecchia.app.database import get_connection


# =========================================================
# CONFIGURAZIONE
# =========================================================

MAX_LEVEL = 999
MAX_STAT = 999

STAT_POINTS_PER_LEVEL = 10


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


def _validate_level(level):

    if not isinstance(level, int):
        raise ValueError(
            "level deve essere un intero."
        )

    if level < 1 or level > MAX_LEVEL:
        raise ValueError(
            f"Il livello deve essere compreso tra 1 e {MAX_LEVEL}."
        )


# =========================================================
# CREAZIONE PROGRESSIONE
# =========================================================

def create_character_progression(
    character_id,
    level=1,
    xp=0,
    xp_required=100
):
    """
    Crea la progressione iniziale del personaggio.
    """

    _validate_character_id(character_id)
    _validate_level(level)

    if not isinstance(xp, int):
        raise ValueError(
            "xp deve essere un intero."
        )

    if xp < 0:
        raise ValueError(
            "XP non può essere negativa."
        )

    if not isinstance(xp_required, int):
        raise ValueError(
            "xp_required deve essere un intero."
        )

    if xp_required < 0:
        raise ValueError(
            "xp_required non può essere negativa."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO character_progression (
                character_id,
                level,
                xp,
                xp_required
            )
            VALUES (?, ?, ?, ?)
        """, (
            character_id,
            level,
            xp,
            xp_required
        ))

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# LETTURA PROGRESSIONE
# =========================================================

def get_character_progression(character_id):

    _validate_character_id(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                character_id,
                level,
                xp,
                xp_required
            FROM character_progression
            WHERE character_id = ?
        """, (
            character_id,
        ))

        return cursor.fetchone()

    finally:

        connection.close()


# =========================================================
# CONVERSIONE IN DICT
# =========================================================

def progression_to_dict(progression):

    if progression is None:
        return None

    return {
        "character_id": progression["character_id"],
        "level": progression["level"],
        "xp": progression["xp"],
        "xp_required": progression["xp_required"]
    }


# =========================================================
# CALCOLO XP
# =========================================================

def calculate_xp_required(level):
    """
    Calcola l'XP necessaria per raggiungere
    il livello successivo.
    """

    _validate_level(level)

    if level >= MAX_LEVEL:
        return 0

    return int(
        100 * (level ** 1.5)
    )


# =========================================================
# PUNTI STATISTICA TOTALI
# =========================================================

def get_level_stat_points(level):
    """
    Restituisce il totale massimo di punti
    statistica disponibili in base al livello.

    Livello 1  -> 10
    Livello 2  -> 20
    Livello 3  -> 30
    ...
    Livello 999 -> 9990
    """

    _validate_level(level)

    return level * STAT_POINTS_PER_LEVEL


# =========================================================
# LIMITE SINGOLA STATISTICA
# =========================================================

def get_level_stat_max(level):
    """
    Restituisce il valore massimo teorico
    di una singola statistica al livello indicato.

    Il limite massimo assoluto è MAX_STAT.
    """

    _validate_level(level)

    # Crescita progressiva fino a MAX_STAT.
    progress = (
        (level - 1)
        / (MAX_LEVEL - 1)
    )

    stat_max = int(
        1
        + (
            (MAX_STAT - 1)
            * (progress ** 1.35)
        )
    )

    return min(
        MAX_STAT,
        max(1, stat_max)
    )


# =========================================================
# PUNTI STATISTICA DISPONIBILI
# =========================================================

def get_available_stat_points(
    level,
    current_total
):
    """
    Calcola quanti punti statistica
    sono ancora disponibili.
    """

    _validate_level(level)

    if not isinstance(current_total, int):
        raise ValueError(
            "current_total deve essere un intero."
        )

    if current_total < 0:
        raise ValueError(
            "current_total non può essere negativo."
        )

    maximum = get_level_stat_points(
        level
    )

    return max(
        0,
        maximum - current_total
    )


# =========================================================
# AGGIORNAMENTO PROGRESSIONE
# =========================================================

def update_character_progression(
    character_id,
    level=None,
    xp=None,
    xp_required=None
):
    """
    Aggiorna i dati della progressione.

    I parametri None non vengono modificati.
    """

    _validate_character_id(character_id)

    fields = []
    values = []

    # -----------------------------------------------------
    # LIVELLO
    # -----------------------------------------------------

    if level is not None:

        _validate_level(level)

        fields.append(
            "level = ?"
        )

        values.append(
            level
        )

    # -----------------------------------------------------
    # XP
    # -----------------------------------------------------

    if xp is not None:

        if not isinstance(xp, int):
            raise ValueError(
                "xp deve essere un intero."
            )

        if xp < 0:
            raise ValueError(
                "XP non può essere negativa."
            )

        fields.append(
            "xp = ?"
        )

        values.append(
            xp
        )

    # -----------------------------------------------------
    # XP RICHIESTA
    # -----------------------------------------------------

    if xp_required is not None:

        if not isinstance(xp_required, int):
            raise ValueError(
                "xp_required deve essere un intero."
            )

        if xp_required < 0:
            raise ValueError(
                "xp_required non può essere negativa."
            )

        fields.append(
            "xp_required = ?"
        )

        values.append(
            xp_required
        )

    if not fields:
        return False

    values.append(
        character_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            UPDATE character_progression
            SET {", ".join(fields)}
            WHERE character_id = ?
            """,
            values
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Progressione del personaggio non trovata."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# AGGIUNTA XP
# =========================================================

def add_character_xp(
    character_id,
    amount
):
    """
    Aggiunge XP al personaggio e gestisce
    automaticamente i level-up.
    """

    _validate_character_id(character_id)

    if not isinstance(amount, int):
        raise ValueError(
            "amount deve essere un intero."
        )

    if amount < 0:
        raise ValueError(
            "amount non può essere negativa."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                level,
                xp,
                xp_required
            FROM character_progression
            WHERE character_id = ?
        """, (
            character_id,
        ))

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                "Progressione del personaggio non trovata."
            )

        level = row["level"]
        xp = row["xp"] + amount

        # -------------------------------------------------
        # LEVEL-UP
        # -------------------------------------------------

        while level < MAX_LEVEL:

            xp_required = calculate_xp_required(
                level
            )

            if xp < xp_required:
                break

            xp -= xp_required

            level += 1

        # -------------------------------------------------
        # LIVELLO MASSIMO
        # -------------------------------------------------

        if level >= MAX_LEVEL:

            level = MAX_LEVEL
            xp = 0
            xp_required = 0

        else:

            xp_required = calculate_xp_required(
                level
            )

        # -------------------------------------------------
        # SALVATAGGIO
        # -------------------------------------------------

        cursor.execute("""
            UPDATE character_progression
            SET
                level = ?,
                xp = ?,
                xp_required = ?
            WHERE character_id = ?
        """, (
            level,
            xp,
            xp_required,
            character_id
        ))

        connection.commit()

        return {
            "character_id": character_id,
            "level": level,
            "xp": xp,
            "xp_required": xp_required
        }

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# IMPOSTAZIONE DIRETTA LIVELLO
# =========================================================

def set_character_level(
    character_id,
    level
):
    """
    Imposta direttamente il livello.

    Utilizzabile per debug, amministrazione
    o eventi speciali.
    """

    _validate_character_id(character_id)
    _validate_level(level)

    xp_required = calculate_xp_required(
        level
    )

    xp = 0

    update_character_progression(
        character_id=character_id,
        level=level,
        xp=xp,
        xp_required=xp_required
    )


# =========================================================
# CONTROLLO LIVELLO MASSIMO
# =========================================================

def is_max_level(level):

    _validate_level(level)

    return level == MAX_LEVEL