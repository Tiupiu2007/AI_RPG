from _Robe_Varie.Roba_Vecchia.app.world_action import execute_world_action
from _Robe_Varie.Roba_Vecchia.app.characters.character_state import save_character_state
from _Robe_Varie.Roba_Vecchia.app.relationships import change_relationship
from _Robe_Varie.Roba_Vecchia.app.memory import create_memory


# =========================================================
# ESECUZIONE PRINCIPALE
# =========================================================

def execute_action(
    action,
    turn_number
):

    if not isinstance(action, dict):

        return {
            "success": False,
            "error": "L'azione deve essere un dizionario."
        }

    action_type = action.get("type")

    # =====================================================
    # WORLD ACTION
    # =====================================================

    if action_type == "world_action":

        return execute_world_action(
            action,
            turn_number=turn_number
        )

    # =====================================================
    # CHARACTER REACTION
    # =====================================================

    if action_type == "character_reaction":

        return execute_character_reaction(action)

    # =====================================================
    # CREATE MEMORY
    # =====================================================

    if action_type == "create_memory":

        return execute_create_memory(action)

    # =====================================================
    # RELATIONSHIP CHANGE
    # =====================================================

    if action_type == "relationship_change":

        return execute_relationship_change(action)

    # =====================================================
    # AZIONE NON SUPPORTATA
    # =====================================================

    return {
        "success": False,
        "error": (
            f"Tipo di azione non supportato: "
            f"{action_type}"
        )
    }


# =========================================================
# CHARACTER REACTION
# =========================================================

def execute_character_reaction(action):

    # =====================================================
    # VALIDAZIONE CAMPI
    # =====================================================

    required_fields = [
        "character_id",
        "emotion",
        "thought",
        "intention",
        "goal"
    ]

    for field in required_fields:

        if field not in action:

            return {
                "success": False,
                "action_type": "character_reaction",
                "error": (
                    f"Campo obbligatorio mancante: "
                    f"{field}"
                )
            }

    character_id = action["character_id"]
    emotion = action["emotion"]
    thought = action["thought"]
    intention = action["intention"]
    goal = action["goal"]

    # =====================================================
    # VALIDAZIONE TIPI
    # =====================================================

    if not isinstance(character_id, int):

        return {
            "success": False,
            "action_type": "character_reaction",
            "error": (
                "character_id deve essere un intero."
            )
        }

    if not isinstance(emotion, str):

        return {
            "success": False,
            "action_type": "character_reaction",
            "error": (
                "emotion deve essere una stringa."
            )
        }

    if not isinstance(thought, str):

        return {
            "success": False,
            "action_type": "character_reaction",
            "error": (
                "thought deve essere una stringa."
            )
        }

    if not isinstance(intention, str):

        return {
            "success": False,
            "action_type": "character_reaction",
            "error": (
                "intention deve essere una stringa."
            )
        }

    if not isinstance(goal, str):

        return {
            "success": False,
            "action_type": "character_reaction",
            "error": (
                "goal deve essere una stringa."
            )
        }

    # =====================================================
    # PULIZIA
    # =====================================================

    emotion = emotion.strip()
    thought = thought.strip()
    intention = intention.strip()
    goal = goal.strip()

    # =====================================================
    # VALIDAZIONE CONTENUTI
    # =====================================================

    if not emotion:

        return {
            "success": False,
            "action_type": "character_reaction",
            "error": "emotion non può essere vuota."
        }

    if not thought:

        return {
            "success": False,
            "action_type": "character_reaction",
            "error": "thought non può essere vuoto."
        }

    if not intention:

        return {
            "success": False,
            "action_type": "character_reaction",
            "error": "intention non può essere vuota."
        }

    # =====================================================
    # SALVATAGGIO STATO
    # =====================================================

    save_character_state(
        character_id=character_id,
        emotion=emotion,
        thought=thought,
        intention=intention,
        goal=goal
    )

    # =====================================================
    # RISULTATO
    # =====================================================

    return {
        "success": True,
        "action_type": "character_reaction",
        "character_id": character_id,
        "emotion": emotion,
        "thought": thought,
        "intention": intention,
        "goal": goal
    }


# =========================================================
# CREATE MEMORY
# =========================================================

def execute_create_memory(action):

    # =====================================================
    # VALIDAZIONE CAMPI
    # =====================================================

    required_fields = [
        "character_id",
        "content",
        "memory_type",
        "importance",
        "secret"
    ]

    for field in required_fields:

        if field not in action:

            return {
                "success": False,
                "action_type": "create_memory",
                "error": (
                    f"Campo obbligatorio mancante: "
                    f"{field}"
                )
            }

    character_id = action["character_id"]
    content = action["content"]
    memory_type = action["memory_type"]
    importance = action["importance"]
    secret = action["secret"]

    # =====================================================
    # VALIDAZIONE CHARACTER ID
    # =====================================================

    if not isinstance(character_id, int):

        return {
            "success": False,
            "action_type": "create_memory",
            "error": (
                "character_id deve essere un intero."
            )
        }

    # =====================================================
    # VALIDAZIONE CONTENT
    # =====================================================

    if not isinstance(content, str):

        return {
            "success": False,
            "action_type": "create_memory",
            "error": (
                "content deve essere una stringa."
            )
        }

    content = content.strip()

    if not content:

        return {
            "success": False,
            "action_type": "create_memory",
            "error": (
                "content non può essere vuoto."
            )
        }

    # =====================================================
    # VALIDAZIONE MEMORY TYPE
    # =====================================================

    if not isinstance(memory_type, str):

        return {
            "success": False,
            "action_type": "create_memory",
            "error": (
                "memory_type deve essere una stringa."
            )
        }

    memory_type = memory_type.strip()

    if not memory_type:

        return {
            "success": False,
            "action_type": "create_memory",
            "error": (
                "memory_type non può essere vuoto."
            )
        }

    # =====================================================
    # VALIDAZIONE IMPORTANCE
    # =====================================================

    if not isinstance(importance, int):

        return {
            "success": False,
            "action_type": "create_memory",
            "error": (
                "importance deve essere un intero."
            )
        }

    if importance < 1 or importance > 10:

        return {
            "success": False,
            "action_type": "create_memory",
            "error": (
                "importance deve essere compreso "
                "tra 1 e 10."
            )
        }

    # =====================================================
    # VALIDAZIONE SECRET
    # =====================================================

    if not isinstance(secret, bool):

        return {
            "success": False,
            "action_type": "create_memory",
            "error": (
                "secret deve essere True oppure False."
            )
        }

    # =====================================================
    # LIMITAZIONE LUNGHEZZA
    # =====================================================

    if len(content) > 500:

        return {
            "success": False,
            "action_type": "create_memory",
            "error": (
                "La memoria è troppo lunga. "
                "Massimo 500 caratteri."
            )
        }

    # =====================================================
    # CREAZIONE MEMORIA
    # =====================================================

    memory_id = create_memory(
        character_id=character_id,
        content=content,
        memory_type=memory_type,
        importance=importance,
        is_secret=secret
    )

    # =====================================================
    # RISULTATO
    # =====================================================

    return {
        "success": True,
        "action_type": "create_memory",
        "memory_id": memory_id,
        "character_id": character_id,
        "content": content,
        "memory_type": memory_type,
        "importance": importance,
        "secret": secret
    }


# =========================================================
# RELATIONSHIP CHANGE
# =========================================================

def execute_relationship_change(action):

    # =====================================================
    # VALIDAZIONE CAMPI
    # =====================================================

    required_fields = [
        "character_a_id",
        "character_b_id"
    ]

    for field in required_fields:

        if field not in action:

            return {
                "success": False,
                "action_type": "relationship_change",
                "error": (
                    f"Campo obbligatorio mancante: "
                    f"{field}"
                )
            }

    character_a_id = action["character_a_id"]
    character_b_id = action["character_b_id"]

    # =====================================================
    # VALIDAZIONE ID
    # =====================================================

    if not isinstance(character_a_id, int):

        return {
            "success": False,
            "action_type": "relationship_change",
            "error": (
                "character_a_id deve essere un intero."
            )
        }

    if not isinstance(character_b_id, int):

        return {
            "success": False,
            "action_type": "relationship_change",
            "error": (
                "character_b_id deve essere un intero."
            )
        }

    # =====================================================
    # CONTROLLO PERSONAGGI DIVERSI
    # =====================================================

    if character_a_id == character_b_id:

        return {
            "success": False,
            "action_type": "relationship_change",
            "error": (
                "Un personaggio non può modificare "
                "la relazione con se stesso."
            )
        }

    # =====================================================
    # VALORI RELAZIONE
    # =====================================================

    trust = action.get("trust", 0)
    affection = action.get("affection", 0)
    respect = action.get("respect", 0)
    hostility = action.get("hostility", 0)

    values = {
        "trust": trust,
        "affection": affection,
        "respect": respect,
        "hostility": hostility
    }

    # =====================================================
    # VALIDAZIONE VALORI
    # =====================================================

    for name, value in values.items():

        if not isinstance(value, int):

            return {
                "success": False,
                "action_type": "relationship_change",
                "error": (
                    f"{name} deve essere un intero."
                )
            }

    # =====================================================
    # EVITA AZIONI VUOTE
    # =====================================================

    if (
        trust == 0
        and affection == 0
        and respect == 0
        and hostility == 0
    ):

        return {
            "success": False,
            "action_type": "relationship_change",
            "error": (
                "La modifica della relazione "
                "non contiene alcun cambiamento."
            )
        }

    # =====================================================
    # LIMITAZIONE CAMBIAMENTO
    # =====================================================

    max_change = 10

    for name, value in values.items():

        if abs(value) > max_change:

            return {
                "success": False,
                "action_type": "relationship_change",
                "error": (
                    f"La modifica di {name} non può "
                    f"superare ±{max_change}."
                )
            }

    # =====================================================
    # MODIFICA RELAZIONE
    # =====================================================

    result = change_relationship(
        character_a_id=character_a_id,
        character_b_id=character_b_id,
        trust=trust,
        affection=affection,
        respect=respect,
        hostility=hostility
    )

    # =====================================================
    # RISULTATO
    # =====================================================

    return {
        "success": True,
        "action_type": "relationship_change",
        "character_a_id": character_a_id,
        "character_b_id": character_b_id,
        "trust": result["trust"],
        "affection": result["affection"],
        "respect": result["respect"],
        "hostility": result["hostility"]
    }