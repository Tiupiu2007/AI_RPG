from _Robe_Varie.Roba_Vecchia.app.world_state import get_world_state


# =========================================================
# PERSONAGGI COINVOLTI
# =========================================================

def detect_involved_characters(character_id, player_input):
    """
    Determina quali personaggi presenti nella stessa area
    sono esplicitamente coinvolti nell'azione del giocatore.

    Il personaggio interpretato viene escluso automaticamente.
    """

    if not isinstance(player_input, str):
        return []

    world_state = get_world_state(character_id)

    characters = world_state.get("characters", [])

    involved = []

    player_input_lower = player_input.lower()

    for character in characters:

        # -------------------------------------------------
        # ID
        # -------------------------------------------------

        current_character_id = character.get("id")

        if current_character_id == character_id:
            continue

        # -------------------------------------------------
        # NOME
        # -------------------------------------------------

        character_name = character.get("name")

        if not character_name:
            continue

        character_name_lower = character_name.lower()

        # -------------------------------------------------
        # CONTROLLO PRESENZA NEL TESTO
        # -------------------------------------------------

        if character_name_lower in player_input_lower:

            involved.append(character)

    return involved