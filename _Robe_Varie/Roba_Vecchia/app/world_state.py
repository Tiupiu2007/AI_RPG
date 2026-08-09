from _Robe_Varie.Roba_Vecchia.app.database import get_connection


def get_character_location(character_id):
    """
    Restituisce l'ID del luogo in cui si trova un personaggio.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT location_id
        FROM characters
        WHERE id = ?
    """, (character_id,))

    row = cursor.fetchone()

    connection.close()

    if row is None:
        return None

    return row["location_id"]


def get_characters_at_location(location_id):
    """
    Restituisce tutti i personaggi vivi presenti
    nello stesso luogo.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            description,
            alive,
            location_id
        FROM characters
        WHERE location_id = ?
        AND alive = 1
        ORDER BY id ASC
    """, (location_id,))

    rows = cursor.fetchall()

    connection.close()

    characters = []

    for row in rows:
        characters.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "alive": bool(row["alive"]),
            "location_id": row["location_id"]
        })

    return characters


def get_characters_near(character_id):
    """
    Restituisce i personaggi vivi presenti nello stesso
    luogo del personaggio indicato.

    Il personaggio stesso viene escluso.
    """

    location_id = get_character_location(character_id)

    if location_id is None:
        return []

    characters = get_characters_at_location(location_id)

    return [
        character
        for character in characters
        if character["id"] != character_id
    ]


def get_world_state(character_id):
    """
    Restituisce lo stato del mondo rilevante per il personaggio.
    """

    location_id = get_character_location(character_id)

    if location_id is None:
        raise ValueError("Personaggio o luogo non trovato.")

    nearby_characters = get_characters_near(character_id)

    return {
        "location_id": location_id,
        "characters": nearby_characters
    }