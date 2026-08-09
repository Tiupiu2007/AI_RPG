# region IMPORT

from _Robe_Varie.Roba_Vecchia.app.database import get_connection

# endregion


# region CREAZIONE PERSONAGGIO

def create_character(
    name,
    description="",
    location_id=None,
    surname=None,
    age=None,
    sex=None,
    gender=None,
    species="human",
    appearance="",
    voice=""
):
    """
    Crea un nuovo personaggio.

    Questo file gestisce esclusivamente l'identità
    fondamentale del personaggio.

    alive viene impostato automaticamente a 1.

    Ritorna:
        int: ID del personaggio creato.
    """

    # -------------------------------------------------
    # VALIDAZIONE
    # -------------------------------------------------

    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "Il nome del personaggio è obbligatorio."
        )

    if not isinstance(description, str):
        raise ValueError(
            "description deve essere una stringa."
        )

    if age is not None:

        if not isinstance(age, int):
            raise ValueError(
                "age deve essere un intero oppure None."
            )

        if age < 0:
            raise ValueError(
                "age non può essere negativo."
            )

    # -------------------------------------------------
    # DATABASE
    # -------------------------------------------------

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO characters (
                name,
                surname,
                age,
                sex,
                gender,
                species,
                description,
                appearance,
                voice,
                location_id,
                alive
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            name.strip(),
            surname,
            age,
            sex,
            gender,
            species,
            description,
            appearance,
            voice,
            location_id
        ))

        character_id = cursor.lastrowid

        connection.commit()

        return character_id

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# endregion


# region LETTURA PERSONAGGIO

def get_character(character_id):
    """
    Recupera l'identità completa di un personaggio.

    Ritorna:
        dict | None
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                surname,
                age,
                sex,
                gender,
                species,
                description,
                appearance,
                voice,
                location_id,
                alive
            FROM characters
            WHERE id = ?
        """, (
            character_id,
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "surname": row["surname"],
            "age": row["age"],
            "sex": row["sex"],
            "gender": row["gender"],
            "species": row["species"],
            "description": row["description"],
            "appearance": row["appearance"],
            "voice": row["voice"],
            "location_id": row["location_id"],
            "alive": bool(row["alive"])
        }

    finally:

        connection.close()


# endregion


# region AGGIORNAMENTO IDENTITÀ

def update_character(
    character_id,
    name=None,
    surname=None,
    age=None,
    sex=None,
    gender=None,
    species=None,
    description=None,
    appearance=None,
    voice=None,
    location_id=None
):
    """
    Aggiorna i dati dell'identità del personaggio.

    I parametri None non vengono modificati.

    alive viene gestito separatamente.
    """

    fields = []
    values = []

    # -------------------------------------------------
    # NOME
    # -------------------------------------------------

    if name is not None:

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "name deve essere una stringa non vuota."
            )

        fields.append("name = ?")
        values.append(name.strip())

    # -------------------------------------------------
    # COGNOME
    # -------------------------------------------------

    if surname is not None:

        fields.append("surname = ?")
        values.append(surname)

    # -------------------------------------------------
    # ETÀ
    # -------------------------------------------------

    if age is not None:

        if not isinstance(age, int) or age < 0:
            raise ValueError(
                "age deve essere un intero non negativo."
            )

        fields.append("age = ?")
        values.append(age)

    # -------------------------------------------------
    # SESSO
    # -------------------------------------------------

    if sex is not None:

        fields.append("sex = ?")
        values.append(sex)

    # -------------------------------------------------
    # GENERE
    # -------------------------------------------------

    if gender is not None:

        fields.append("gender = ?")
        values.append(gender)

    # -------------------------------------------------
    # SPECIE
    # -------------------------------------------------

    if species is not None:

        fields.append("species = ?")
        values.append(species)

    # -------------------------------------------------
    # DESCRIZIONE
    # -------------------------------------------------

    if description is not None:

        if not isinstance(description, str):
            raise ValueError(
                "description deve essere una stringa."
            )

        fields.append("description = ?")
        values.append(description)

    # -------------------------------------------------
    # ASPETTO
    # -------------------------------------------------

    if appearance is not None:

        fields.append("appearance = ?")
        values.append(appearance)

    # -------------------------------------------------
    # VOCE
    # -------------------------------------------------

    if voice is not None:

        fields.append("voice = ?")
        values.append(voice)

    # -------------------------------------------------
    # LOCATION
    # -------------------------------------------------

    if location_id is not None:

        fields.append("location_id = ?")
        values.append(location_id)

    # -------------------------------------------------
    # NIENTE DA MODIFICARE
    # -------------------------------------------------

    if not fields:
        return False

    # -------------------------------------------------
    # DATABASE
    # -------------------------------------------------

    values.append(character_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            UPDATE characters
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values
        )

        connection.commit()

        return cursor.rowcount > 0

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# endregion


# region VITA / MORTE

def is_character_alive(character_id):
    """
    Controlla se il personaggio è vivo.
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT alive
            FROM characters
            WHERE id = ?
        """, (
            character_id,
        ))

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                "Personaggio non trovato."
            )

        return bool(row["alive"])

    finally:

        connection.close()


def set_character_alive(
    character_id,
    alive
):
    """
    Imposta lo stato vivo/morto.

    Il personaggio morto NON viene eliminato
    dal database.
    """

    if not isinstance(alive, bool):
        raise ValueError(
            "alive deve essere un booleano."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            UPDATE characters
            SET alive = ?
            WHERE id = ?
        """, (
            1 if alive else 0,
            character_id
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                "Personaggio non trovato."
            )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# endregion