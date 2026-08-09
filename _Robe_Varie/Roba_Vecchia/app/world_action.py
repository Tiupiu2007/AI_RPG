from _Robe_Varie.Roba_Vecchia.app.database import get_connection

from _Robe_Varie.Roba_Vecchia.app.world_events import create_world_event


# =========================================================
# ESECUZIONE WORLD ACTION
# =========================================================

def execute_world_action(
    action,
    turn_number
):
    """
    Esegue un'azione del mondo e registra
    l'evento realmente avvenuto.

    Azioni supportate:
        - speak
        - approach
        - move
    """

    # =====================================================
    # VALIDAZIONE GENERALE
    # =====================================================

    if not isinstance(action, dict):
        raise ValueError(
            "action deve essere un dizionario."
        )

    if not isinstance(turn_number, int):
        raise ValueError(
            "turn_number deve essere un intero."
        )

    action_name = action.get("action")
    character_id = action.get("character_id")

    if not isinstance(action_name, str):
        raise ValueError(
            "action deve essere una stringa."
        )

    action_name = action_name.strip()

    if not action_name:
        raise ValueError(
            "action non può essere vuota."
        )

    if not isinstance(character_id, int):
        raise ValueError(
            "character_id deve essere un intero."
        )

    # =====================================================
    # DATABASE
    # =====================================================

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # =================================================
        # CONTROLLO PERSONAGGIO
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                location_id,
                alive
            FROM characters
            WHERE id = ?
            """,
            (
                character_id,
            )
        )

        character = cursor.fetchone()

        if character is None:
            raise ValueError(
                "Il personaggio non esiste."
            )

        if not bool(character["alive"]):
            raise ValueError(
                "Il personaggio è morto."
            )

        current_location_id = character["location_id"]

        # =================================================
        # SPEAK
        # =================================================

        if action_name == "speak":

            target_id = action.get("target_id")
            dialogue = action.get("dialogue")

            # ---------------------------------------------
            # VALIDAZIONE TARGET
            # ---------------------------------------------

            if not isinstance(target_id, int):
                raise ValueError(
                    "target_id deve essere un intero."
                )

            if target_id == character_id:
                raise ValueError(
                    "Un personaggio non può parlare con se stesso."
                )

            # ---------------------------------------------
            # CONTROLLO TARGET
            # ---------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    location_id,
                    alive
                FROM characters
                WHERE id = ?
                """,
                (
                    target_id,
                )
            )

            target = cursor.fetchone()

            if target is None:
                raise ValueError(
                    "Il personaggio bersaglio non esiste."
                )

            if not bool(target["alive"]):
                raise ValueError(
                    "Il personaggio bersaglio è morto."
                )

            # ---------------------------------------------
            # VALIDAZIONE DIALOGO
            # ---------------------------------------------

            if not isinstance(dialogue, str):
                raise ValueError(
                    "dialogue deve essere una stringa."
                )

            dialogue = dialogue.strip()

            if not dialogue:
                raise ValueError(
                    "dialogue non può essere vuoto."
                )

            if len(dialogue) > 1000:
                raise ValueError(
                    "dialogue non può superare "
                    "1000 caratteri."
                )

            # ---------------------------------------------
            # CONTROLLO LOCATION
            # ---------------------------------------------

            if (
                target["location_id"]
                != current_location_id
            ):
                raise ValueError(
                    "Il personaggio bersaglio "
                    "non si trova nella stessa location."
                )

            # ---------------------------------------------
            # WORLD EVENT
            # ---------------------------------------------

            event_id = create_world_event(
                turn_number=turn_number,
                event_type="character_spoke",
                actor_id=character_id,
                target_id=target_id,
                location_id=current_location_id,
                data={
                    "dialogue": dialogue
                },
                connection=connection
            )

            connection.commit()

            return {
                "success": True,
                "action_type": "world_action",
                "action": "speak",
                "character_id": character_id,
                "target_id": target_id,
                "dialogue": dialogue,
                "world_event_id": event_id
            }

        # =================================================
        # APPROACH
        # =================================================

        if action_name == "approach":

            target_id = action.get("target_id")

            # ---------------------------------------------
            # VALIDAZIONE TARGET
            # ---------------------------------------------

            if not isinstance(target_id, int):
                raise ValueError(
                    "target_id deve essere un intero."
                )

            if target_id == character_id:
                raise ValueError(
                    "Un personaggio non può avvicinarsi "
                    "a se stesso."
                )

            # ---------------------------------------------
            # CONTROLLO TARGET
            # ---------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    location_id,
                    alive
                FROM characters
                WHERE id = ?
                """,
                (
                    target_id,
                )
            )

            target = cursor.fetchone()

            if target is None:
                raise ValueError(
                    "Il personaggio bersaglio non esiste."
                )

            if not bool(target["alive"]):
                raise ValueError(
                    "Il personaggio bersaglio è morto."
                )

            # ---------------------------------------------
            # CONTROLLO LOCATION
            # ---------------------------------------------

            if (
                target["location_id"]
                != current_location_id
            ):
                raise ValueError(
                    "Il personaggio bersaglio "
                    "non si trova nella stessa location."
                )

            # ---------------------------------------------
            # WORLD EVENT
            # ---------------------------------------------

            event_id = create_world_event(
                turn_number=turn_number,
                event_type="character_approached",
                actor_id=character_id,
                target_id=target_id,
                location_id=current_location_id,
                data={},
                connection=connection
            )

            connection.commit()

            return {
                "success": True,
                "action_type": "world_action",
                "action": "approach",
                "character_id": character_id,
                "target_id": target_id,
                "world_event_id": event_id
            }

        # =================================================
        # MOVE
        # =================================================

        if action_name == "move":

            location_id = action.get("location_id")

            # ---------------------------------------------
            # VALIDAZIONE LOCATION
            # ---------------------------------------------

            if not isinstance(location_id, int):
                raise ValueError(
                    "location_id deve essere un intero."
                )

            if location_id <= 0:
                raise ValueError(
                    "location_id deve essere maggiore di 0."
                )

            # ---------------------------------------------
            # CONTROLLO LOCATION
            # ---------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM locations
                WHERE id = ?
                """,
                (
                    location_id,
                )
            )

            location = cursor.fetchone()

            if location is None:
                raise ValueError(
                    "La location di destinazione non esiste."
                )

            # ---------------------------------------------
            # CONTROLLO SPOSTAMENTO
            # ---------------------------------------------

            if location_id == current_location_id:
                raise ValueError(
                    "Il personaggio si trova già "
                    "in questa location."
                )

            old_location_id = current_location_id

            # ---------------------------------------------
            # SPOSTAMENTO
            # ---------------------------------------------

            cursor.execute(
                """
                UPDATE characters
                SET location_id = ?
                WHERE id = ?
                """,
                (
                    location_id,
                    character_id
                )
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    "Il personaggio non è stato spostato."
                )

            # ---------------------------------------------
            # WORLD EVENT
            # ---------------------------------------------

            event_id = create_world_event(
                turn_number=turn_number,
                event_type="character_moved",
                actor_id=character_id,
                target_id=None,
                location_id=location_id,
                data={
                    "from_location_id": old_location_id,
                    "to_location_id": location_id
                },
                connection=connection
            )

            # ---------------------------------------------
            # COMMIT UNICO
            # ---------------------------------------------

            connection.commit()

            return {
                "success": True,
                "action_type": "world_action",
                "action": "move",
                "character_id": character_id,
                "location_id": location_id,
                "previous_location_id": old_location_id,
                "world_event_id": event_id
            }

        # =================================================
        # AZIONE NON SUPPORTATA
        # =================================================

        return {
            "success": False,
            "action_type": "world_action",
            "error": (
                f"Azione world_action non supportata: "
                f"{action_name}"
            )
        }

    # =====================================================
    # ERRORE
    # =================================================

    except Exception:

        connection.rollback()

        raise

    # =====================================================
    # CHIUSURA
    # =====================================================

    finally:

        connection.close()