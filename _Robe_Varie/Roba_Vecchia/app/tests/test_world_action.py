import json

from _Robe_Varie.Roba_Vecchia.app.database import get_connection
from _Robe_Varie.Roba_Vecchia.app.characters.character import create_character

from _Robe_Varie.Roba_Vecchia.app.action_executor import execute_action

from _Robe_Varie.Roba_Vecchia.app.world_events import (
    get_world_event,
    get_recent_world_events,
    get_world_events_by_turn
)


# =========================================================
# CREAZIONE LOCATION DI TEST
# =========================================================

def create_test_locations():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM locations
            ORDER BY id ASC
            LIMIT 2
        """)

        rows = cursor.fetchall()

        if len(rows) >= 2:

            return rows[0]["id"], rows[1]["id"]

        raise ValueError(
            "Servono almeno 2 location nel database "
            "per eseguire questo test."
        )

    finally:

        connection.close()


# =========================================================
# CREAZIONE PERSONAGGI DI TEST
# =========================================================

def create_test_characters(location_id):

    character_a_id = create_character(
        name="Test Character A",
        description="Personaggio utilizzato per i test.",
        location_id=location_id
    )

    character_b_id = create_character(
        name="Test Character B",
        description="Personaggio utilizzato per i test.",
        location_id=location_id
    )

    print()
    print("========================================")
    print("PERSONAGGI DI TEST")
    print("========================================")
    print(f"Character A: {character_a_id}")
    print(f"Character B: {character_b_id}")

    return character_a_id, character_b_id


# =========================================================
# TEST SPEAK
# =========================================================

def test_speak(
    character_a_id,
    character_b_id
):

    action = {
        "type": "world_action",
        "action": "speak",
        "character_id": character_a_id,
        "target_id": character_b_id,
        "dialogue": "Ciao, come stai?"
    }

    result = execute_action(
        action,
        turn_number=1
    )

    print()
    print("=== SPEAK ===")
    print(result)

    assert result["success"] is True
    assert result["action_type"] == "world_action"
    assert result["action"] == "speak"
    assert result["character_id"] == character_a_id
    assert result["target_id"] == character_b_id
    assert result["dialogue"] == "Ciao, come stai?"

    assert isinstance(
        result["world_event_id"],
        int
    )

    return result["world_event_id"]


# =========================================================
# TEST APPROACH
# =========================================================

def test_approach(
    character_a_id,
    character_b_id
):

    action = {
        "type": "world_action",
        "action": "approach",
        "character_id": character_a_id,
        "target_id": character_b_id
    }

    result = execute_action(
        action,
        turn_number=2
    )

    print()
    print("=== APPROACH ===")
    print(result)

    assert result["success"] is True
    assert result["action_type"] == "world_action"
    assert result["action"] == "approach"
    assert result["character_id"] == character_a_id
    assert result["target_id"] == character_b_id

    assert isinstance(
        result["world_event_id"],
        int
    )

    return result["world_event_id"]


# =========================================================
# TEST MOVE
# =========================================================

def test_move(
    character_a_id,
    destination_location_id
):

    action = {
        "type": "world_action",
        "action": "move",
        "character_id": character_a_id,
        "location_id": destination_location_id
    }

    result = execute_action(
        action,
        turn_number=3
    )

    print()
    print("=== MOVE ===")
    print(result)

    assert result["success"] is True
    assert result["action_type"] == "world_action"
    assert result["action"] == "move"
    assert result["character_id"] == character_a_id
    assert result["location_id"] == destination_location_id

    assert isinstance(
        result["previous_location_id"],
        int
    )

    assert isinstance(
        result["world_event_id"],
        int
    )

    return result["world_event_id"]


# =========================================================
# LETTURA SINGOLO EVENTO
# =========================================================

def test_get_world_event(event_id):

    event = get_world_event(
        event_id
    )

    print()
    print("=== GET WORLD EVENT ===")

    print(
        json.dumps(
            event,
            indent=2,
            ensure_ascii=False
        )
    )

    assert event is not None
    assert event["id"] == event_id

    return event


# =========================================================
# EVENTI RECENTI
# =========================================================

def test_recent_world_events():

    events = get_recent_world_events(
        limit=10
    )

    print()
    print("=== RECENT WORLD EVENTS ===")

    print(
        json.dumps(
            events,
            indent=2,
            ensure_ascii=False
        )
    )

    assert isinstance(
        events,
        list
    )

    assert len(events) >= 3

    return events


# =========================================================
# EVENTI DEL TURNO
# =========================================================

def test_world_events_by_turn():

    events = get_world_events_by_turn(
        turn_number=1
    )

    print()
    print("=== WORLD EVENTS - TURNO 1 ===")

    print(
        json.dumps(
            events,
            indent=2,
            ensure_ascii=False
        )
    )

    assert isinstance(
        events,
        list
    )

    assert len(events) >= 1

    return events


# =========================================================
# CONTROLLO DATABASE
# =========================================================

def test_database_events():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                turn_number,
                event_type,
                actor_id,
                target_id,
                location_id,
                data_json,
                created_at
            FROM world_events
            ORDER BY id ASC
        """)

        rows = cursor.fetchall()

        print()
        print("=== DATABASE WORLD_EVENTS ===")

        for row in rows:

            print(
                json.dumps(
                    dict(row),
                    indent=2,
                    ensure_ascii=False
                )
            )

        assert len(rows) >= 3

    finally:

        connection.close()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    location_a_id, location_b_id = (
        create_test_locations()
    )

    print()
    print("========================================")
    print("LOCATION DI TEST")
    print("========================================")
    print(f"Location A: {location_a_id}")
    print(f"Location B: {location_b_id}")

    character_a_id, character_b_id = (
        create_test_characters(
            location_a_id
        )
    )

    speak_event_id = test_speak(
        character_a_id,
        character_b_id
    )

    approach_event_id = test_approach(
        character_a_id,
        character_b_id
    )

    move_event_id = test_move(
        character_a_id,
        location_b_id
    )

    test_get_world_event(
        speak_event_id
    )

    test_get_world_event(
        approach_event_id
    )

    test_get_world_event(
        move_event_id
    )

    test_recent_world_events()

    test_world_events_by_turn()

    test_database_events()

    print()
    print("========================================")
    print("TUTTI I TEST WORLD ACTION SUPERATI")
    print("========================================")