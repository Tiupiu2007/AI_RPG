from _Robe_Varie.Roba_Vecchia.app.database import get_connection


def create_location(name, description):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO locations (
            name,
            description
        )
        VALUES (?, ?)
    """, (
        name,
        description
    ))

    location_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return location_id


def get_location(location_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            description
        FROM locations
        WHERE id = ?
    """, (location_id,))

    location = cursor.fetchone()

    connection.close()

    return location


def get_all_locations():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            description
        FROM locations
        ORDER BY id
    """)

    locations = cursor.fetchall()

    connection.close()

    return locations