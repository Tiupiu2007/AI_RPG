import unittest

from app.game_engine import execute_action, ensure_game_state, validate_action
from app.combat.combat_models import combatant_from_character


class GameEngineContractTests(unittest.TestCase):
    def test_player_state_defaults_are_authoritative(self):
        extra = {}
        ensure_game_state(extra)
        self.assertEqual(extra["conditions"]["health"], 100)
        self.assertEqual(extra["game_state"]["turn"], 0)

    def test_move_uses_only_available_destinations(self):
        extra = {"available_location_ids": ["room_2"]}
        ensure_game_state(extra)
        self.assertTrue(validate_action(extra, {
            "type": "move",
            "target_id": "room_2",
            "target_text": None,
            "parameters": {},
        })["valid"])
        self.assertFalse(validate_action(extra, {
            "type": "move",
            "target_id": "secret_room",
            "target_text": None,
            "parameters": {},
        })["valid"])

    def test_use_item_cannot_create_items(self):
        extra = {"inventory": {"potion": 1}}
        ensure_game_state(extra)
        result = execute_action(extra, {
            "type": "use_item",
            "target_id": "potion",
            "target_text": None,
            "parameters": {},
        })
        self.assertTrue(result["valid"])
        self.assertEqual(extra["inventory"], {})

        denied = execute_action(extra, {
            "type": "use_item",
            "target_id": "potion",
            "target_text": None,
            "parameters": {},
        })
        self.assertFalse(denied["valid"])

    def test_combat_uses_max_resources_from_character_state(self):
        character = {
            "id": 1,
            "identity": {"name": "Test"},
            "extra": {
                "statistics": {},
                "conditions": {
                    "health": 40,
                    "max_health": 100,
                    "stamina": 20,
                    "max_stamina": 80,
                    "mana": 10,
                    "max_mana": 50,
                },
            },
        }
        combatant = combatant_from_character(character)
        self.assertEqual(combatant.health, 40)
        self.assertEqual(combatant.max_health, 100)
        self.assertEqual(combatant.stamina, 20)
        self.assertEqual(combatant.max_stamina, 80)
        self.assertEqual(combatant.mana, 10)
        self.assertEqual(combatant.max_mana, 50)


if __name__ == "__main__":
    unittest.main()
