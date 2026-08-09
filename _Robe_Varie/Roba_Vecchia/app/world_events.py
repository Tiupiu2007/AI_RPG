import json

from _Robe_Varie.Roba_Vecchia.app.database import get_connection


# =========================================================
# CREAZIONE WORLD EVENT
# =========================================================

def create_world_event(
    turn_number,
    event_type,
    actor_id=None,
    target_id=None,
    location_id=None,
    data=None,
    connection=None
):
    """
    Registra un evento realmente avvenuto nel mondo.

    Se viene fornita una connection esterna,
    l'evento viene inserito nella stessa transazione.
    """

    if not isinstance(turn_number, int):
        raise ValueError(
            "turn_number deve essere un intero."
        )

    if not isinstance(event_type, str):
        raise ValueError(
            "event_type deve essere una stringa."
        )

    event_type = event_type.strip()

    if not event_type:
        raise ValueError(
            "event_type non può essere vuoto."
        )

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(
            "data deve essere un dizionario."
        )

    data_json = json.dumps(
        data,
        ensure_ascii=False
    )

    own_connection = connection is None

    if own_connection:
        connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO world_events (
                turn_number,
                event_type,
                actor_id,
                target_id,
                location_id,
                data_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            turn_number,
            event_type,
            actor_id,
            target_id,
            location_id,
            data_json
        ))

        event_id = cursor.lastrowid

        if own_connection:
            connection.commit()

        return event_id

    except Exception:

        if own_connection:
            connection.rollback()

        raise

    finally:

        if own_connection:
            connection.close()


# =========================================================
# OTTIENI WORLD EVENT
# =========================================================

def get_world_event(event_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                turn_number,
                event_type,
                actor_id,
                target_id,
                location_id,
                data_json,
                created_at
            FROM world_events
            WHERE id = ?
        """, (
            event_id,
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "turn_number": row["turn_number"],
            "event_type": row["event_type"],
            "actor_id": row["actor_id"],
            "target_id": row["target_id"],
            "location_id": row["location_id"],
            "data": json.loads(
                row["data_json"]
            ),
            "created_at": row["created_at"]
        }

    finally:

        connection.close()


# =========================================================
# EVENTI RECENTI
# =========================================================

def get_recent_world_events(limit=10):

    if not isinstance(limit, int):
        raise ValueError(
            "limit deve essere un intero."
        )

    if limit <= 0:
        raise ValueError(
            "limit deve essere maggiore di 0."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                turn_number,
                event_type,
                actor_id,
                target_id,
                location_id,
                data_json,
                created_at
            FROM world_events
            ORDER BY turn_number DESC, id DESC
            LIMIT ?
        """, (
            limit,
        ))

        rows = cursor.fetchall()

        events = []

        for row in reversed(rows):

            events.append({
                "id": row["id"],
                "turn_number": row["turn_number"],
                "event_type": row["event_type"],
                "actor_id": row["actor_id"],
                "target_id": row["target_id"],
                "location_id": row["location_id"],
                "data": json.loads(
                    row["data_json"]
                ),
                "created_at": row["created_at"]
            })

        return events

    finally:

        connection.close()


# =========================================================
# EVENTI DI UN TURNO
# =========================================================

def get_world_events_by_turn(turn_number):

    if not isinstance(turn_number, int):
        raise ValueError(
            "turn_number deve essere un intero."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                turn_number,
                event_type,
                actor_id,
                target_id,
                location_id,
                data_json,
                created_at
            FROM world_events
            WHERE turn_number = ?
            ORDER BY id ASC
        """, (
            turn_number,
        ))

        rows = cursor.fetchall()

        events = []

        for row in rows:

            events.append({
                "id": row["id"],
                "turn_number": row["turn_number"],
                "event_type": row["event_type"],
                "actor_id": row["actor_id"],
                "target_id": row["target_id"],
                "location_id": row["location_id"],
                "data": json.loads(
                    row["data_json"]
                ),
                "created_at": row["created_at"]
            })

        return events

    finally:

        connection.close()