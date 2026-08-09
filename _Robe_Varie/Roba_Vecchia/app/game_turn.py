import json

from _Robe_Varie.Roba_Vecchia.app.scene_context import get_scene_context

from _Robe_Varie.Roba_Vecchia.app.ai_provider import ask_character

from _Robe_Varie.Roba_Vecchia.app.action_validator import validate_action

from _Robe_Varie.Roba_Vecchia.app.action_executor import execute_action

from _Robe_Varie.Roba_Vecchia.app.game_history import (
    create_game_event,
    get_current_turn
)


def process_turn(
    reacting_character_id,
    player_id,
    player_input
):

    # =====================================================
    # 1. TURNO
    # =====================================================

    turn_number = get_current_turn() + 1

    # =====================================================
    # 2. CONTESTO
    # =====================================================

    try:

        context = get_scene_context(
            reacting_character_id=reacting_character_id,
            player_id=player_id,
            player_input=player_input
        )

    except Exception as error:

        return {
            "success": False,
            "stage": "context",
            "error": "Errore nella costruzione del contesto.",
            "details": str(error)
        }

    # =====================================================
    # 3. AI
    # =====================================================

    try:

        ai_response = ask_character(
            context,
            player_input
        )

    except Exception as error:

        return {
            "success": False,
            "stage": "ai_request",
            "error": (
                "Errore durante la comunicazione "
                "con Ollama."
            ),
            "details": str(error)
        }

    # =====================================================
    # 4. JSON
    # =====================================================

    try:

        decision = json.loads(
            ai_response
        )

    except json.JSONDecodeError as error:

        return {
            "success": False,
            "stage": "ai_response",
            "error": (
                "Ollama non ha restituito "
                "JSON valido."
            ),
            "raw_response": ai_response,
            "details": str(error)
        }

    # =====================================================
    # 5. STRUTTURA
    # =====================================================

    if not isinstance(
        decision,
        dict
    ):

        return {
            "success": False,
            "stage": "structure",
            "error": (
                "La risposta dell'AI deve essere "
                "un oggetto JSON."
            )
        }

    if "narration" not in decision:

        return {
            "success": False,
            "stage": "structure",
            "error": (
                "Campo 'narration' mancante."
            )
        }

    if not isinstance(
        decision["narration"],
        str
    ):

        return {
            "success": False,
            "stage": "structure",
            "error": (
                "Il campo 'narration' deve "
                "essere una stringa."
            )
        }

    if "actions" not in decision:

        return {
            "success": False,
            "stage": "structure",
            "error": (
                "Campo 'actions' mancante."
            )
        }

    if not isinstance(
        decision["actions"],
        list
    ):

        return {
            "success": False,
            "stage": "structure",
            "error": (
                "Il campo 'actions' deve "
                "essere una lista."
            )
        }

    # =====================================================
    # 6. NORMALIZZAZIONE
    # =====================================================

    for action in decision["actions"]:

        if not isinstance(
            action,
            dict
        ):
            continue

        action_type = action.get("type")

        # -------------------------------------------------
        # REAZIONE
        # -------------------------------------------------

        if action_type == "character_reaction":

            action["character_id"] = (
                reacting_character_id
            )

        # -------------------------------------------------
        # RELAZIONE
        # -------------------------------------------------

        elif action_type == "relationship_change":

            action.setdefault(
                "trust",
                0
            )

            action.setdefault(
                "affection",
                0
            )

            action.setdefault(
                "respect",
                0
            )

            action.setdefault(
                "hostility",
                0
            )

    # =====================================================
    # 7. VALIDAZIONE
    # =====================================================

    validation_results = []

    for action in decision["actions"]:

        validation = validate_action(
            action,
            reacting_character_id=(
                reacting_character_id
            )
        )

        validation_results.append({
            "action": action,
            "validation": validation
        })

        if not validation["valid"]:

            return {
                "success": False,
                "stage": "validation",
                "error": (
                    "Una delle azioni "
                    "non è valida."
                ),
                "results": validation_results,
                "narration": (
                    decision["narration"]
                )
            }

    # =====================================================
    # 8. ESECUZIONE
    # =====================================================

    execution_results = []

    for action in decision["actions"]:

        try:

            result = execute_action(
                action,
                turn_number=turn_number
            )

        except Exception as error:

            return {
                "success": False,
                "stage": "execution",
                "error": (
                    "Errore durante "
                    "l'esecuzione di un'azione."
                ),
                "action": action,
                "executions": execution_results,
                "details": str(error),
                "narration": (
                    decision["narration"]
                )
            }

        execution_results.append(
            result
        )

        if not result.get(
            "success",
            False
        ):

            return {
                "success": False,
                "stage": "execution",
                "error": (
                    "Un'azione non è stata "
                    "eseguita correttamente."
                ),
                "action": action,
                "execution": result,
                "executions": execution_results,
                "narration": (
                    decision["narration"]
                )
            }

    # =====================================================
    # 9. SALVATAGGIO CRONOLOGIA
    # =====================================================

    try:

        create_game_event(
            turn_number=turn_number,
            player_input=player_input,
            narration=decision["narration"],
            actions=decision["actions"]
        )

    except Exception as error:

        return {
            "success": False,
            "stage": "history",
            "error": (
                "Le azioni sono state eseguite, "
                "ma il turno non è stato salvato "
                "nella cronologia."
            ),
            "details": str(error),
            "turn_number": turn_number,
            "narration": decision["narration"],
            "actions": decision["actions"],
            "executions": execution_results
        }

    # =====================================================
    # 10. RISULTATO
    # =====================================================

    return {
        "success": True,
        "turn_number": turn_number,
        "narration": decision["narration"],
        "actions": decision["actions"],
        "executions": execution_results
    }