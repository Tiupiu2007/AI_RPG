from _Robe_Varie.Roba_Vecchia.app.database import get_connection


def _validate_character_id(character_id):

    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    if character_id <= 0:
        raise ValueError(
            "character_id deve essere maggiore di 0."
        )


def _validate_value(value, name):

    if not isinstance(value, str):
        raise ValueError(
            f"{name} deve essere una stringa."
        )


def create_character_state(
    character_id,
    emotion="",
    thought="",
    intention="",
    goal=""
):

    _validate_character_id(character_id)

    _validate_value(emotion, "emotion")
    _validate_value(thought, "thought")
    _validate_value(intention, "intention")
    _validate_value(goal, "goal")

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
            INSERT INTO character_states (
                character_id,
                emotion,
                thought,
                intention,
                goal
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            character_id,
            emotion,
            thought,
            intention,
            goal
        ))

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_character_state(character_id):

    _validate_character_id(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                character_id,
                emotion,
                thought,
                intention,
                goal
            FROM character_states
            WHERE character_id = ?
        """, (
            character_id,
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:

        connection.close()


def update_character_state(
    character_id,
    emotion=None,
    thought=None,
    intention=None,
    goal=None
):

    _validate_character_id(character_id)

    fields = []
    values = []

    if emotion is not None:

        _validate_value(
            emotion,
            "emotion"
        )

        fields.append("emotion = ?")
        values.append(emotion)

    if thought is not None:

        _validate_value(
            thought,
            "thought"
        )

        fields.append("thought = ?")
        values.append(thought)

    if intention is not None:

        _validate_value(
            intention,
            "intention"
        )

        fields.append("intention = ?")
        values.append(intention)

    if goal is not None:

        _validate_value(
            goal,
            "goal"
        )

        fields.append("goal = ?")
        values.append(goal)

    if not fields:
        return False

    values.append(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            UPDATE character_states
            SET {", ".join(fields)}
            WHERE character_id = ?
            """,
            values
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Stato del personaggio non trovato."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def save_character_state(
    character_id,
    emotion="",
    thought="",
    intention="",
    goal=""
):

    _validate_character_id(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO character_states (
                character_id,
                emotion,
                thought,
                intention,
                goal
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(character_id)
            DO UPDATE SET
                emotion = excluded.emotion,
                thought = excluded.thought,
                intention = excluded.intention,
                goal = excluded.goal
        """, (
            character_id,
            emotion,
            thought,
            intention,
            goal
        ))

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def clear_character_state(character_id):

    _validate_character_id(character_id)

    return update_character_state(
        character_id=character_id,
        emotion="",
        thought="",
        intention="",
        goal=""
    )


def delete_character_state(character_id):

    _validate_character_id(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM character_states
            WHERE character_id = ?
        """, (
            character_id,
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                "Stato del personaggio non trovato."
            )

        connection.commit()

        return True

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def state_to_dict(state):

    if state is None:
        return None

    return {
        "character_id": state["character_id"],
        "emotion": state["emotion"],
        "thought": state["thought"],
        "intention": state["intention"],
        "goal": state["goal"]
    }