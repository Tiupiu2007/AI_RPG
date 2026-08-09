from _Robe_Varie.Roba_Vecchia.app.database import initialize_database, reset_database

from _Robe_Varie.Roba_Vecchia.app.world import create_location
from _Robe_Varie.Roba_Vecchia.app.characters.character import create_character
from _Robe_Varie.Roba_Vecchia.app.characters.character_state import create_character_state
from _Robe_Varie.Roba_Vecchia.app.memory import create_memory
from _Robe_Varie.Roba_Vecchia.app.relationships import create_relationship


# =========================================================
# CREA NUOVA PARTITA
# =========================================================

def create_new_game():
    """
    Crea una nuova partita da zero.

    La partita comprende:

    - database pulito
    - mondo iniziale
    - personaggi
    - stato iniziale
    - memorie iniziali
    - relazioni iniziali

    Ritorna gli ID degli elementi creati.
    """

    # =====================================================
    # DATABASE
    # =====================================================

    initialize_database()
    reset_database()

    # =====================================================
    # MONDO
    # =====================================================

    castle_id = create_location(
        name="Castello",
        description="Un enorme castello fortificato."
    )

    # =====================================================
    # PERSONAGGI
    # =====================================================

    lilith_id = create_character(
        name="Lilith",
        description="Una donna misteriosa e prudente.",
        location_id=castle_id
    )

    protagonist_id = create_character(
        name="Protagonista",
        description="Il protagonista della storia.",
        location_id=castle_id
    )

    # =====================================================
    # STATO INIZIALE DI LILITH
    # =====================================================

    create_character_state(
        character_id=lilith_id,

        emotion="sospettosa",

        thought="Non so ancora cosa voglia.",

        intention="Capire le sue intenzioni.",

        goal="Proteggere il castello."
    )

    # =====================================================
    # MEMORIA INIZIALE DI LILITH
    # =====================================================

    create_memory(
        character_id=lilith_id,

        content=(
            "Il protagonista ha affermato di essere il re."
        ),

        memory_type="evento",

        importance=7,

        is_secret=True
    )

    # =====================================================
    # RELAZIONE LILITH -> PROTAGONISTA
    # =====================================================

    create_relationship(
        character_a_id=lilith_id,
        character_b_id=protagonist_id,

        trust=40,
        affection=20,
        respect=55,
        hostility=5
    )

    # =====================================================
    # RISULTATO
    # =====================================================

    return {
        "current_turn": 0,

        "castle_id": castle_id,

        "lilith_id": lilith_id,

        "protagonist_id": protagonist_id
    }