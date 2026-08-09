from _Robe_Varie.Roba_Vecchia.app.database import get_connection
from _Robe_Varie.Roba_Vecchia.app.game_history import get_recent_game_events


# =========================================================
# CONTESTO DEL PERSONAGGIO
# =========================================================

def get_character_context(character_id):
    """
    Costruisce il contesto completo necessario all'AI
    per interpretare un singolo personaggio.
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # =================================================
        # PERSONAGGIO + LUOGO
        # =================================================

        cursor.execute("""
            SELECT
                c.id,
                c.name,
                c.description,
                c.alive,
                c.location_id,
                l.name AS location_name,
                l.description AS location_description
            FROM characters c
            LEFT JOIN locations l
                ON c.location_id = l.id
            WHERE c.id = ?
        """, (
            character_id,
        ))

        character = cursor.fetchone()

        if character is None:
            raise ValueError(
                "Personaggio non trovato."
            )

        # =================================================
        # STATO INTERNO
        # =================================================

        cursor.execute("""
            SELECT
                emotion,
                thought,
                intention,
                goal
            FROM character_states
            WHERE character_id = ?
        """, (
            character_id,
        ))

        state = cursor.fetchone()

        # =================================================
        # MEMORIE
        # =================================================

        cursor.execute("""
            SELECT
                id,
                content,
                memory_type,
                importance,
                is_secret
            FROM memories
            WHERE character_id = ?
            ORDER BY importance DESC, id ASC
        """, (
            character_id,
        ))

        memories = cursor.fetchall()

        # =================================================
        # RELAZIONI
        # =================================================

        cursor.execute("""
            SELECT
                r.id,
                r.character_a_id,
                r.character_b_id,
                r.trust,
                r.affection,
                r.respect,
                r.hostility,

                CASE
                    WHEN r.character_a_id = ?
                    THEN r.character_b_id
                    ELSE r.character_a_id
                END AS other_character_id

            FROM relationships r

            WHERE r.character_a_id = ?
               OR r.character_b_id = ?
        """, (
            character_id,
            character_id,
            character_id
        ))

        relationships = cursor.fetchall()

        # =================================================
        # PERSONAGGI PRESENTI
        # =================================================

        cursor.execute("""
            SELECT
                id,
                name,
                description,
                alive,
                location_id
            FROM characters
            WHERE location_id = ?
              AND id != ?
            ORDER BY id ASC
        """, (
            character["location_id"],
            character_id
        ))

        characters_present = cursor.fetchall()

        # =================================================
        # COSTRUZIONE CONTESTO
        # =================================================

        context = {

            # =============================================
            # PERSONAGGIO
            # =============================================

            "character": {
                "id": character["id"],
                "name": character["name"],
                "description": character["description"],
                "alive": bool(character["alive"]),

                "location": {
                    "id": character["location_id"],
                    "name": character["location_name"],
                    "description": character["location_description"]
                }
            },

            # =============================================
            # STATO
            # =============================================

            "state": None,

            # =============================================
            # MEMORIE
            # =============================================

            "memories": [],

            # =============================================
            # RELAZIONI
            # =============================================

            "relationships": [],

            # =============================================
            # PERSONAGGI PRESENTI
            # =============================================

            "characters_present": [],

            # =============================================
            # CONVERSAZIONE RECENTE
            # =============================================

            "recent_conversation": [],

            # =============================================
            # EVENTI RECENTI
            # =============================================

            "recent_events": []
        }

        # =================================================
        # STATO
        # =================================================

        if state is not None:

            context["state"] = {
                "emotion": state["emotion"],
                "thought": state["thought"],
                "intention": state["intention"],
                "goal": state["goal"]
            }

        # =================================================
        # MEMORIE
        # =================================================

        for memory in memories:

            context["memories"].append({

                "id": memory["id"],

                "content": memory["content"],

                "type": memory["memory_type"],

                "importance": memory["importance"],

                "secret": bool(
                    memory["is_secret"]
                )
            })

        # =================================================
        # RELAZIONI
        # =================================================

        for relationship in relationships:

            other_character_id = (
                relationship["other_character_id"]
            )

            cursor.execute("""
                SELECT
                    id,
                    name,
                    description,
                    alive
                FROM characters
                WHERE id = ?
            """, (
                other_character_id,
            ))

            other_character = cursor.fetchone()

            if other_character is None:
                continue

            context["relationships"].append({

                "id": relationship["id"],

                "character_id": other_character["id"],

                "name": other_character["name"],

                "description": other_character["description"],

                "alive": bool(
                    other_character["alive"]
                ),

                "trust": relationship["trust"],

                "affection": relationship["affection"],

                "respect": relationship["respect"],

                "hostility": relationship["hostility"]
            })

        # =================================================
        # PERSONAGGI PRESENTI
        # =================================================

        for present_character in characters_present:

            context["characters_present"].append({

                "id": present_character["id"],

                "name": present_character["name"],

                "description": present_character["description"],

                "alive": bool(
                    present_character["alive"]
                ),

                "location_id": present_character["location_id"]
            })

    finally:
        connection.close()

    # =====================================================
    # CRONOLOGIA RECENTE
    # =====================================================

    recent_events = get_recent_game_events(
        limit=10
    )

    for event in recent_events:

        # ---------------------------------------------
        # EVENTO COMPLETO
        # ---------------------------------------------

        context["recent_events"].append({

            "id": event["id"],

            "turn_number": event["turn_number"],

            "player_input": event["player_input"],

            "narration": event["narration"],

            "actions": event["actions"],

            "created_at": event["created_at"]
        })

        # ---------------------------------------------
        # CONVERSAZIONE PULITA
        # ---------------------------------------------

        context["recent_conversation"].append({

            "turn": event["turn_number"],

            "player": event["player_input"],

            "character": event["narration"]
        })

    # =====================================================
    # RISULTATO
    # =====================================================

    return context

