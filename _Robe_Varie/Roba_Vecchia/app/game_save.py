from _Robe_Varie.Roba_Vecchia.app.database import get_connection


# =========================================================
# OTTIENI TURNO ATTUALE
# =========================================================

def get_current_turn():
    """
    Restituisce il numero dell'ultimo turno salvato.

    Se non esistono ancora eventi:
        ritorna 0
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT MAX(turn_number)
            FROM game_events
        """)

        result = cursor.fetchone()

        if result is None or result[0] is None:
            return 0

        return result[0]

    finally:
        connection.close()


# =========================================================
# SALVA STATO PARTITA
# =========================================================

def save_game():
    """
    Restituisce le informazioni necessarie
    per identificare lo stato attuale della partita.
    """

    return {
        "current_turn": get_current_turn()
    }