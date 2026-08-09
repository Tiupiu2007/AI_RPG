from _Robe_Varie.Roba_Vecchia.app.database import get_connection
from _Robe_Varie.Roba_Vecchia.app.context import get_character_context
from _Robe_Varie.Roba_Vecchia.app.game_history import get_recent_game_events


# =========================================================
# CARICA PARTITA
# =========================================================

def load_game():
    """
    Carica le informazioni principali della partita.

    Ritorna:
        dict con:
        - current_turn
        - characters
        - locations
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # =================================================
        # PERSONAGGI
        # =================================================

        cursor.execute("""
            SELECT
                id,
                name,
                description,
                location_id,
                alive
            FROM characters
            ORDER BY id ASC
        """)

        characters = cursor.fetchall()

        # =================================================
        # LUOGHI
        # =================================================

        cursor.execute("""
            SELECT
                id,
                name,
                description
            FROM locations
            ORDER BY id ASC
        """)

        locations = cursor.fetchall()

        # =================================================
        # ULTIMO TURNO
        # =================================================

        cursor.execute("""
            SELECT MAX(turn_number)
            FROM game_events
        """)

        result = cursor.fetchone()

        if result is None or result[0] is None:
            current_turn = 0
        else:
            current_turn = result[0]

        # =================================================
        # RISULTATO
        # =================================================

        return {
            "current_turn": current_turn,

            "characters": [
                dict(character)
                for character in characters
            ],

            "locations": [
                dict(location)
                for location in locations
            ]
        }

    finally:
        connection.close()


# =========================================================
# CARICA PERSONAGGIO
# =========================================================

def find_character_id_by_name(name):
    """
    Cerca l'ID di un personaggio a partire dal nome.

    Serve per recuperare i personaggi principali
    (es. Lilith, Protagonista) quando si riprende
    una partita salvata.

    Ritorna:
        int | None
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM characters
            WHERE name = ?
            LIMIT 1
        """, (
            name,
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return row["id"]

    finally:
        connection.close()


def load_character(character_id):
    """
    Carica il contesto completo di un personaggio.

    Il contesto comprende:

    - identità
    - descrizione
    - stato
    - luogo
    - memorie
    - relazioni
    - personaggi presenti
    - eventi recenti
    """

    return get_character_context(character_id)


# =========================================================
# CARICA CRONOLOGIA RECENTE
# =========================================================

def load_recent_history(limit=10):
    """
    Carica gli ultimi eventi della partita.

    Ritorna una lista di eventi.
    """

    if not isinstance(limit, int):
        raise ValueError(
            "limit deve essere un intero."
        )

    if limit <= 0:
        raise ValueError(
            "limit deve essere maggiore di 0."
        )

    return get_recent_game_events(limit)