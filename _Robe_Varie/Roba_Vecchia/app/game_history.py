import json

from _Robe_Varie.Roba_Vecchia.app.database import get_connection


# =========================================================
# TURNO CORRENTE
# =========================================================

def get_current_turn():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT MAX(turn_number)
            FROM game_events
        """)

        result = cursor.fetchone()

        if result[0] is None:
            return 0

        return result[0]

    finally:
        connection.close()


# =========================================================
# PROSSIMO TURNO
# =========================================================

def get_next_turn():

    return get_current_turn() + 1


# =========================================================
# CREAZIONE EVENTO
# =========================================================

def create_game_event(
    turn_number,
    player_input,
    narration,
    actions
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        actions_json = json.dumps(
            actions,
            ensure_ascii=False
        )

        cursor.execute("""
            INSERT INTO game_events (
                turn_number,
                player_input,
                narration,
                actions_json
            )
            VALUES (?, ?, ?, ?)
        """, (
            turn_number,
            player_input,
            narration,
            actions_json
        ))

        event_id = cursor.lastrowid

        connection.commit()

        return event_id

    except Exception:

        connection.rollback()
        raise

    finally:
        connection.close()


# =========================================================
# OTTIENI EVENTO
# =========================================================

def get_game_event(event_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                turn_number,
                player_input,
                narration,
                actions_json,
                created_at
            FROM game_events
            WHERE id = ?
        """, (event_id,))

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "turn_number": row["turn_number"],
            "player_input": row["player_input"],
            "narration": row["narration"],
            "actions": json.loads(
                row["actions_json"]
            ),
            "created_at": row["created_at"]
        }

    finally:
        connection.close()


# =========================================================
# CRONOLOGIA COMPLETA
# =========================================================

def get_game_history():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                turn_number,
                player_input,
                narration,
                actions_json,
                created_at
            FROM game_events
            ORDER BY turn_number ASC, id ASC
        """)

        rows = cursor.fetchall()

        events = []

        for row in rows:

            events.append({

                "id": row["id"],

                "turn_number": row["turn_number"],

                "player_input": row["player_input"],

                "narration": row["narration"],

                "actions": json.loads(
                    row["actions_json"]
                ),

                "created_at": row["created_at"]
            })

        return events

    finally:
        connection.close()


# =========================================================
# EVENTI RECENTI
# =========================================================

def get_recent_game_events(limit=10):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                turn_number,
                player_input,
                narration,
                actions_json,
                created_at
            FROM game_events
            ORDER BY turn_number DESC, id DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()

        events = []

        for row in reversed(rows):

            events.append({

                "id": row["id"],

                "turn_number": row["turn_number"],

                "player_input": row["player_input"],

                "narration": row["narration"],

                "actions": json.loads(
                    row["actions_json"]
                ),

                "created_at": row["created_at"]
            })

        return events

    finally:
        connection.close()