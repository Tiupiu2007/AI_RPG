from _Robe_Varie.Roba_Vecchia.app.database import get_connection


# =========================================================
# AZIONI CONSENTITE
# =========================================================

ALLOWED_ACTION_TYPES = {
    "world_action",
    "character_reaction",
    "create_memory",
    "relationship_change"
}

ALLOWED_WORLD_ACTIONS = {
    "speak",
    "approach",
    "move"
}


# =========================================================
# LIMITI
# =========================================================

MIN_RELATIONSHIP_CHANGE = -30
MAX_RELATIONSHIP_CHANGE = 30

MIN_MEMORY_IMPORTANCE = 1
MAX_MEMORY_IMPORTANCE = 10


# =========================================================
# VALIDAZIONE PRINCIPALE
# =========================================================

def validate_action(
    action,
    reacting_character_id=None
):
    """
    Valida una qualsiasi azione prodotta dall'AI.
    """

    if not isinstance(action, dict):

        return {
            "valid": False,
            "errors": [
                "L'azione deve essere un dizionario."
            ]
        }

    action_type = action.get("type")

    if action_type not in ALLOWED_ACTION_TYPES:

        return {
            "valid": False,
            "errors": [
                f"Tipo di azione non consentito: {action_type}"
            ]
        }

    # =====================================================
    # WORLD ACTION
    # =====================================================

    if action_type == "world_action":

        return validate_world_action(action)

    # =====================================================
    # CHARACTER REACTION
    # =====================================================

    if action_type == "character_reaction":

        return validate_character_reaction(
            action,
            reacting_character_id
        )

    # =====================================================
    # CREATE MEMORY
    # =====================================================

    if action_type == "create_memory":

        return validate_create_memory(
            action,
            reacting_character_id
        )

    # =====================================================
    # RELATIONSHIP CHANGE
    # =====================================================

    if action_type == "relationship_change":

        return validate_relationship_change(
            action,
            reacting_character_id
        )

    return {
        "valid": False,
        "errors": [
            "Tipo di azione non gestito."
        ]
    }


# =========================================================
# WORLD ACTION
# =========================================================

def validate_world_action(action):

    errors = []

    action_name = action.get("action")

    if action_name not in ALLOWED_WORLD_ACTIONS:

        return {
            "valid": False,
            "errors": [
                f"Azione world non consentita: {action_name}"
            ]
        }

    character_id = action.get("character_id")

    if character_id is None:

        errors.append(
            "Campo obbligatorio mancante: character_id"
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # =================================================
        # PERSONAGGIO
        # =================================================

        character = None

        if character_id is not None:

            cursor.execute("""
                SELECT
                    id,
                    alive,
                    location_id
                FROM characters
                WHERE id = ?
            """, (
                character_id,
            ))

            character = cursor.fetchone()

            if character is None:

                errors.append(
                    "Il personaggio indicato non esiste."
                )

            elif not character["alive"]:

                errors.append(
                    "Il personaggio è morto."
                )

        # =================================================
        # SPEAK / APPROACH
        # =================================================

        if action_name in {
            "speak",
            "approach"
        }:

            target_id = action.get("target_id")

            if target_id is None:

                errors.append(
                    "Campo obbligatorio mancante: target_id"
                )

            else:

                cursor.execute("""
                    SELECT
                        id,
                        alive,
                        location_id
                    FROM characters
                    WHERE id = ?
                """, (
                    target_id,
                ))

                target = cursor.fetchone()

                if target is None:

                    errors.append(
                        "Il personaggio bersaglio "
                        "non esiste."
                    )

                elif not target["alive"]:

                    errors.append(
                        "Il personaggio bersaglio "
                        "è morto."
                    )

                elif (
                    character is not None
                    and character["location_id"]
                    != target["location_id"]
                ):

                    errors.append(
                        "Il personaggio e il bersaglio "
                        "non si trovano nello stesso luogo."
                    )

        # =================================================
        # SPEAK
        # =================================================

        if action_name == "speak":

            dialogue = action.get("dialogue")

            if dialogue is None:

                errors.append(
                    "Campo obbligatorio mancante: dialogue"
                )

            elif not isinstance(dialogue, str):

                errors.append(
                    "dialogue deve essere una stringa."
                )

            elif not dialogue.strip():

                errors.append(
                    "dialogue non può essere vuoto."
                )

        # =================================================
        # MOVE
        # =================================================

        if action_name == "move":

            location_id = action.get("location_id")

            if location_id is None:

                errors.append(
                    "Campo obbligatorio mancante: location_id"
                )

            else:

                cursor.execute("""
                    SELECT id
                    FROM locations
                    WHERE id = ?
                """, (
                    location_id,
                ))

                location = cursor.fetchone()

                if location is None:

                    errors.append(
                        "Il luogo indicato non esiste."
                    )

    finally:

        connection.close()

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


# =========================================================
# CHARACTER REACTION
# =========================================================

def validate_character_reaction(
    action,
    reacting_character_id
):

    errors = []

    character_id = action.get("character_id")

    # =====================================================
    # IDENTITÀ
    # =====================================================

    if character_id is None:

        errors.append(
            "character_id mancante."
        )

    elif reacting_character_id is not None:

        if character_id != reacting_character_id:

            errors.append(
                "La character_reaction deve appartenere "
                "esattamente al personaggio che sta reagendo."
            )

    # =====================================================
    # STATO
    # =====================================================

    required_fields = [
        "emotion",
        "thought",
        "intention",
        "goal"
    ]

    for field in required_fields:

        if field not in action:

            errors.append(
                f"Campo obbligatorio mancante: {field}"
            )

        elif not isinstance(
            action[field],
            str
        ):

            errors.append(
                f"{field} deve essere una stringa."
            )

        elif not action[field].strip():

            errors.append(
                f"{field} non può essere vuoto."
            )

    # =====================================================
    # DATABASE
    # =====================================================

    if character_id is not None:

        connection = get_connection()
        cursor = connection.cursor()

        try:

            cursor.execute("""
                SELECT
                    id,
                    alive
                FROM characters
                WHERE id = ?
            """, (
                character_id,
            ))

            character = cursor.fetchone()

            if character is None:

                errors.append(
                    "Il personaggio della reazione "
                    "non esiste."
                )

            elif not character["alive"]:

                errors.append(
                    "Il personaggio della reazione "
                    "è morto."
                )

        finally:

            connection.close()

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


# =========================================================
# CREATE MEMORY
# =========================================================

def validate_create_memory(
    action,
    reacting_character_id=None
):

    errors = []

    character_id = action.get("character_id")

    # =====================================================
    # IDENTITÀ
    # =====================================================

    if character_id is None:

        errors.append(
            "character_id mancante."
        )

    elif reacting_character_id is not None:

        if character_id != reacting_character_id:

            errors.append(
                "La memoria deve appartenere "
                "esattamente al personaggio che sta reagendo."
            )

    # =====================================================
    # CONTENT
    # =====================================================

    content = action.get("content")

    if content is None:

        errors.append(
            "Campo obbligatorio mancante: content"
        )

    elif not isinstance(content, str):

        errors.append(
            "content deve essere una stringa."
        )

    elif not content.strip():

        errors.append(
            "content non può essere vuoto."
        )

    # =====================================================
    # MEMORY TYPE
    # =====================================================

    memory_type = action.get("memory_type")

    if memory_type is None:

        errors.append(
            "Campo obbligatorio mancante: memory_type"
        )

    elif not isinstance(memory_type, str):

        errors.append(
            "memory_type deve essere una stringa."
        )

    elif not memory_type.strip():

        errors.append(
            "memory_type non può essere vuoto."
        )

    # =====================================================
    # IMPORTANCE
    # =====================================================

    importance = action.get("importance")

    if importance is None:

        errors.append(
            "Campo obbligatorio mancante: importance"
        )

    elif isinstance(importance, bool):

        errors.append(
            "importance deve essere un intero."
        )

    elif not isinstance(importance, int):

        errors.append(
            "importance deve essere un intero."
        )

    elif not (
        MIN_MEMORY_IMPORTANCE
        <= importance
        <= MAX_MEMORY_IMPORTANCE
    ):

        errors.append(
            "importance deve essere compreso "
            f"tra {MIN_MEMORY_IMPORTANCE} e "
            f"{MAX_MEMORY_IMPORTANCE}."
        )

    # =====================================================
    # SECRET
    # =====================================================

    if "secret" not in action:

        errors.append(
            "Campo obbligatorio mancante: secret"
        )

    elif not isinstance(
        action["secret"],
        bool
    ):

        errors.append(
            "secret deve essere true oppure false."
        )

    # =====================================================
    # DATABASE
    # =====================================================

    if character_id is not None:

        connection = get_connection()
        cursor = connection.cursor()

        try:

            cursor.execute("""
                SELECT
                    id,
                    alive
                FROM characters
                WHERE id = ?
            """, (
                character_id,
            ))

            character = cursor.fetchone()

            if character is None:

                errors.append(
                    "Il personaggio della memoria "
                    "non esiste."
                )

            elif not character["alive"]:

                errors.append(
                    "Il personaggio della memoria "
                    "è morto."
                )

        finally:

            connection.close()

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


# =========================================================
# RELATIONSHIP CHANGE
# =========================================================

def validate_relationship_change(
    action,
    reacting_character_id=None
):

    errors = []

    character_a_id = action.get(
        "character_a_id"
    )

    character_b_id = action.get(
        "character_b_id"
    )

    # =====================================================
    # ID
    # =====================================================

    if character_a_id is None:

        errors.append(
            "character_a_id mancante."
        )

    if character_b_id is None:

        errors.append(
            "character_b_id mancante."
        )

    # =====================================================
    # PERSONAGGIO A = PERSONAGGIO INTERPRETATO
    # =====================================================

    if (
        character_a_id is not None
        and reacting_character_id is not None
        and character_a_id != reacting_character_id
    ):

        errors.append(
            "character_a_id deve essere il personaggio "
            "attualmente interpretato."
        )

    # =====================================================
    # NON PUÒ ESSERE LO STESSO PERSONAGGIO
    # =====================================================

    if (
        character_a_id is not None
        and character_b_id is not None
        and character_a_id == character_b_id
    ):

        errors.append(
            "Una relazione non può collegare "
            "un personaggio a sé stesso."
        )

    # =====================================================
    # VALORI
    # =====================================================

    relationship_fields = [
        "trust",
        "affection",
        "respect",
        "hostility"
    ]

    for field in relationship_fields:

        value = action.get(field, 0)

        if isinstance(value, bool):

            errors.append(
                f"{field} deve essere un intero."
            )

        elif not isinstance(value, int):

            errors.append(
                f"{field} deve essere un intero."
            )

        elif not (
            MIN_RELATIONSHIP_CHANGE
            <= value
            <= MAX_RELATIONSHIP_CHANGE
        ):

            errors.append(
                f"{field} deve essere compreso "
                f"tra {MIN_RELATIONSHIP_CHANGE} e "
                f"{MAX_RELATIONSHIP_CHANGE}."
            )

    # =====================================================
    # DATABASE
    # =====================================================

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # =================================================
        # PERSONAGGIO A
        # =================================================

        if character_a_id is not None:

            cursor.execute("""
                SELECT
                    id,
                    alive
                FROM characters
                WHERE id = ?
            """, (
                character_a_id,
            ))

            character_a = cursor.fetchone()

            if character_a is None:

                errors.append(
                    f"Personaggio {character_a_id} "
                    "non esiste."
                )

            elif not character_a["alive"]:

                errors.append(
                    f"Personaggio {character_a_id} "
                    "è morto."
                )

        # =================================================
        # PERSONAGGIO B
        # =================================================

        if character_b_id is not None:

            cursor.execute("""
                SELECT
                    id,
                    alive
                FROM characters
                WHERE id = ?
            """, (
                character_b_id,
            ))

            character_b = cursor.fetchone()

            if character_b is None:

                errors.append(
                    f"Personaggio {character_b_id} "
                    "non esiste."
                )

            elif not character_b["alive"]:

                errors.append(
                    f"Personaggio {character_b_id} "
                    "è morto."
                )

        # =================================================
        # RELAZIONE ESISTENTE
        # =================================================

        if (
            character_a_id is not None
            and character_b_id is not None
            and character_a_id != character_b_id
        ):

            cursor.execute("""
                SELECT
                    id
                FROM relationships
                WHERE
                    (
                        character_a_id = ?
                        AND character_b_id = ?
                    )
                    OR
                    (
                        character_a_id = ?
                        AND character_b_id = ?
                    )
            """, (
                character_a_id,
                character_b_id,
                character_b_id,
                character_a_id
            ))

            relationship = cursor.fetchone()

            if relationship is None:

                errors.append(
                    "La relazione indicata non esiste."
                )

    finally:

        connection.close()

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }