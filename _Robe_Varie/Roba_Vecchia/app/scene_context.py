from _Robe_Varie.Roba_Vecchia.app.context import get_character_context
from _Robe_Varie.Roba_Vecchia.app.action_target import detect_involved_characters
from _Robe_Varie.Roba_Vecchia.app.database import get_connection
from _Robe_Varie.Roba_Vecchia.app.game_history import get_recent_game_events


# =========================================================
# INFORMAZIONI BASE PERSONAGGIO
# =========================================================

def get_character_basic_info(character_id):
    """
    Recupera le informazioni essenziali di un personaggio.

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
                description,
                alive,
                location_id
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
            "description": row["description"],
            "alive": bool(row["alive"]),
            "location_id": row["location_id"]
        }

    finally:

        connection.close()


# =========================================================
# NORMALIZZAZIONE PERSONAGGI
# =========================================================

def normalize_character(character):
    """
    Normalizza un personaggio in una struttura sicura
    da passare al contesto AI.
    """

    if not isinstance(character, dict):
        return None

    character_id = character.get("id")

    if not isinstance(character_id, int):
        return None

    return {
        "id": character_id,

        "name": character.get(
            "name",
            ""
        ),

        "description": character.get(
            "description",
            ""
        ),

        "alive": bool(
            character.get(
                "alive",
                True
            )
        ),

        "location_id": character.get(
            "location_id"
        )
    }


# =========================================================
# NORMALIZZAZIONE PERSONAGGI COINVOLTI
# =========================================================

def normalize_involved_characters(
    involved_characters
):
    """
    Normalizza la lista dei personaggi coinvolti
    nell'input del giocatore.
    """

    if not isinstance(
        involved_characters,
        list
    ):
        return []

    normalized = []

    for character in involved_characters:

        normalized_character = normalize_character(
            character
        )

        if normalized_character is None:
            continue

        normalized.append(
            normalized_character
        )

    return normalized


# =========================================================
# CONTESTO DELLA SCENA
# =========================================================

def get_scene_context(
    reacting_character_id,
    player_id,
    player_input
):
    """
    Costruisce il contesto completo della scena.

    reacting_character_id:
        Personaggio che deve reagire.

    player_id:
        Personaggio controllato dal giocatore.

    player_input:
        Messaggio o azione appena compiuta dal giocatore.

    IMPORTANTE:

    Questa funzione costruisce solamente il contesto.

    Non decide cosa deve fare il personaggio.

    Non modifica il database.

    Non esegue azioni.
    """

    # =====================================================
    # VALIDAZIONE INPUT
    # =====================================================

    if not isinstance(
        reacting_character_id,
        int
    ):

        raise ValueError(
            "reacting_character_id deve essere un intero."
        )

    if not isinstance(
        player_id,
        int
    ):

        raise ValueError(
            "player_id deve essere un intero."
        )

    if not isinstance(
        player_input,
        str
    ):

        raise ValueError(
            "player_input deve essere una stringa."
        )

    player_input = player_input.strip()

    if not player_input:

        raise ValueError(
            "player_input non può essere vuoto."
        )

    # =====================================================
    # PERSONAGGIO CHE REAGISCE
    # =====================================================

    character_context = get_character_context(
        reacting_character_id
    )

    if character_context is None:

        raise ValueError(
            "Contesto del personaggio non trovato."
        )

    if not isinstance(
        character_context,
        dict
    ):

        raise ValueError(
            "Il contesto del personaggio deve "
            "essere un dizionario."
        )

    # =====================================================
    # PERSONAGGIO DEL GIOCATORE
    # =====================================================

    player = get_character_basic_info(
        player_id
    )

    if player is None:

        raise ValueError(
            "Personaggio del giocatore non trovato."
        )

    # =====================================================
    # IL PERSONAGGIO NON PUÒ ESSERE SE STESSO
    # =====================================================

    if reacting_character_id == player_id:

        raise ValueError(
            "Il personaggio che reagisce non può "
            "essere lo stesso personaggio controllato "
            "dal giocatore."
        )

    # =====================================================
    # PERSONAGGI COINVOLTI
    # =====================================================

    involved_characters = detect_involved_characters(
        player_id,
        player_input
    )

    normalized_involved_characters = (
        normalize_involved_characters(
            involved_characters
        )
    )

    # =====================================================
    # CRONOLOGIA RECENTE
    # =====================================================
    #
    # Recuperiamo gli eventi recenti per mantenere
    # la continuità della scena.
    #
    # ATTENZIONE:
    #
    # Questa cronologia è ancora una cronologia globale.
    #
    # Non la consideriamo automaticamente come conoscenza
    # del personaggio.
    #
    # Il sistema definitivo dovrà distinguere:
    #
    #   - eventi realmente avvenuti;
    #   - eventi osservati dal personaggio;
    #   - eventi raccontati al personaggio;
    #   - memorie personali;
    #   - informazioni sconosciute.
    #
    # Questo verrà gestito quando avremo verificato
    # game_history e memory.
    #
    # =====================================================

    recent_events = get_recent_game_events(
        limit=10
    )

    if recent_events is None:

        recent_events = []

    if not isinstance(
        recent_events,
        list
    ):

        recent_events = []

    # =====================================================
    # CRONOLOGIA DELLA CONVERSAZIONE
    # =====================================================
    #
    # Se il contesto proveniente da context.py contiene già
    # una conversazione specifica del personaggio, la
    # manteniamo.
    #
    # Non la sostituiamo con gli eventi globali.
    #
    # =====================================================

    recent_conversation = (
        character_context.get(
            "recent_conversation",
            []
        )
    )

    if not isinstance(
        recent_conversation,
        list
    ):

        recent_conversation = []

    # =====================================================
    # SCENA
    # =====================================================

    character_context["scene"] = {

        # -------------------------------------------------
        # PERSONAGGIO DEL GIOCATORE
        # -------------------------------------------------

        "player": player,

        # -------------------------------------------------
        # PERSONAGGIO INTERPRETATO DALL'AI
        # -------------------------------------------------

        "reacting_character_id": (
            reacting_character_id
        ),

        # -------------------------------------------------
        # ID DEL GIOCATORE
        # -------------------------------------------------

        "player_id": player_id,

        # -------------------------------------------------
        # INPUT ATTUALE
        # -------------------------------------------------

        "player_input": player_input,

        # -------------------------------------------------
        # PERSONAGGI COINVOLTI
        # -------------------------------------------------

        "involved_characters": (
            normalized_involved_characters
        )
    }

    # =====================================================
    # CRONOLOGIA
    # =====================================================
    #
    # Questi dati vengono mantenuti separati.
    #
    # recent_conversation:
    #    conversazione utile alla continuità del dialogo.
    #
    # recent_events:
    #    eventi recenti del gioco.
    #
    # La distinzione è importante perché un evento globale
    # non significa automaticamente che il personaggio
    # lo conosca.
    #
    # =====================================================

    character_context["recent_conversation"] = (
        recent_conversation
    )

    character_context["recent_events"] = (
        recent_events
    )

    # =====================================================
    # RISULTATO
    # =====================================================

    return character_context

