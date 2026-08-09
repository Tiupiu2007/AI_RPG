from _Robe_Varie.Roba_Vecchia.app.database import get_connection


MAX_STAT = 999

BASE_STAT_NAMES = (
    "strength",
    "constitution",
    "speed",
    "intelligence",
    "perception",
    "willpower",
    "luck"
)


def _validate_character_id(character_id):

    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    if character_id <= 0:
        raise ValueError(
            "character_id deve essere maggiore di 0."
        )


def _validate_stat_name(stat_name):

    if stat_name not in BASE_STAT_NAMES:
        raise ValueError(
            f"Statistica non valida: {stat_name}"
        )


def _validate_stat_value(value):

    if not isinstance(value, int):
        raise ValueError(
            "Il valore della statistica deve essere un intero."
        )

    if value < 0:
        raise ValueError(
            "Il valore della statistica non può essere negativo."
        )

    if value > MAX_STAT:
        raise ValueError(
            f"Il valore massimo della statistica è {MAX_STAT}."
        )


def create_character_statistics(
    character_id,
    strength=1,
    constitution=1,
    speed=1,
    intelligence=1,
    perception=1,
    willpower=1,
    luck=1
):

    _validate_character_id(character_id)

    stats = {
        "strength": strength,
        "constitution": constitution,
        "speed": speed,
        "intelligence": intelligence,
        "perception": perception,
        "willpower": willpower,
        "luck": luck
    }

    for stat_name, value in stats.items():
        _validate_stat_value(value)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO character_statistics (
                character_id,
                strength,
                constitution,
                speed,
                intelligence,
                perception,
                willpower,
                luck
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            character_id,
            strength,
            constitution,
            speed,
            intelligence,
            perception,
            willpower,
            luck
        ))

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_character_statistics(character_id):

    _validate_character_id(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                character_id,
                strength,
                constitution,
                speed,
                intelligence,
                perception,
                willpower,
                luck
            FROM character_statistics
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


def get_character_stat(
    character_id,
    stat_name
):

    _validate_character_id(character_id)
    _validate_stat_name(stat_name)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            SELECT {stat_name}
            FROM character_statistics
            WHERE character_id = ?
            """,
            (
                character_id,
            )
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                "Statistiche del personaggio non trovate."
            )

        return row[stat_name]

    finally:

        connection.close()


def set_character_stat(
    character_id,
    stat_name,
    value
):

    _validate_character_id(character_id)
    _validate_stat_name(stat_name)
    _validate_stat_value(value)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            UPDATE character_statistics
            SET {stat_name} = ?
            WHERE character_id = ?
            """,
            (
                value,
                character_id
            )
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Statistiche del personaggio non trovate."
            )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def modify_character_stat(
    character_id,
    stat_name,
    amount
):

    _validate_character_id(character_id)
    _validate_stat_name(stat_name)

    if not isinstance(amount, int):
        raise ValueError(
            "amount deve essere un intero."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            SELECT {stat_name}
            FROM character_statistics
            WHERE character_id = ?
            """,
            (
                character_id,
            )
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                "Statistiche del personaggio non trovate."
            )

        current_value = row[stat_name]
        new_value = current_value + amount

        new_value = max(
            0,
            min(MAX_STAT, new_value)
        )

        cursor.execute(
            f"""
            UPDATE character_statistics
            SET {stat_name} = ?
            WHERE character_id = ?
            """,
            (
                new_value,
                character_id
            )
        )

        connection.commit()

        return new_value

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_total_stat_points(character_id):

    _validate_character_id(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                strength,
                constitution,
                speed,
                intelligence,
                perception,
                willpower,
                luck
            FROM character_statistics
            WHERE character_id = ?
        """, (
            character_id,
        ))

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                "Statistiche del personaggio non trovate."
            )

        return sum(
            row[stat_name]
            for stat_name in BASE_STAT_NAMES
        )

    finally:

        connection.close()


def get_all_character_stats(character_id):

    statistics = get_character_statistics(
        character_id
    )

    if statistics is None:
        return None

    return {
        stat_name: statistics[stat_name]
        for stat_name in BASE_STAT_NAMES
    }