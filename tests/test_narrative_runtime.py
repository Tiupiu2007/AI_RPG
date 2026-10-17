import unittest
from unittest.mock import patch

from app.game_engine.quests import active_quests, apply_quest_updates


class NarrativeRuntimeTests(unittest.TestCase):
    def test_action_options_are_normalized_to_four(self):
        from app.story_chat import _format_action_options, _parse_action_options

        options = _parse_action_options(["prima", "seconda"])
        self.assertEqual(len(options), 4)
        rendered = _format_action_options(options)
        self.assertIn("1. **Prudente / razionale:** prima", rendered)
        self.assertIn("2. **Aggressiva / rischiosa:** seconda", rendered)
        self.assertIn("3. **Sociale / esplorativa:**", rendered)
        self.assertIn("4. **Libera / creativa:**", rendered)
        self.assertTrue(rendered.endswith("**Oppure fai quello che vuoi.**"))
    def test_narration_player_control_guard_detects_invented_state(self):
        from app.story_chat import _narration_needs_repair

        self.assertTrue(
            _narration_needs_repair(
                "Non hai scelto questa strada e sei qui davanti al cancello.",
                "guardo in torno in cerca di qualcuno",
            )
        )
        self.assertTrue(
            _narration_needs_repair(
                "Il tuo passo è leggero e ti avvicini alla porta.",
                "guardo la porta",
            )
        )
        self.assertFalse(
            _narration_needs_repair(
                "Guardi intorno. A pochi passi c'è una donna seduta su un gradino.",
                "guardo in torno in cerca di qualcuno",
            )
        )

    def test_narration_guard_ignores_npc_dialogue(self):
        from app.story_chat import _narration_needs_repair

        self.assertFalse(
            _narration_needs_repair(
                "La donna ti guarda.",
                "guardo in torno",
            )
        )
        self.assertFalse(
            _narration_needs_repair(
                """Donna:
— «Ti seguo fino alla porta.»""",
                "guardo in torno",
            )
        )
        self.assertTrue(
            _narration_needs_repair(
                "Ti avvicini alla porta.",
                "guardo la porta",
            )
        )

    def test_quest_lifecycle_is_persistent(self):
        extra = {}
        created = apply_quest_updates(
            extra,
            [{
                "id": "find_key",
                "title": "Trova la chiave",
                "description": "Recupera la chiave della cantina.",
                "status": "active",
                "objectives": [
                    {"id": "key", "text": "Recupera la chiave", "done": False},
                ],
            }],
            1,
        )
        self.assertEqual(len(created), 1)
        self.assertEqual(active_quests(extra)[0]["id"], "find_key")

        apply_quest_updates(
            extra,
            [{
                "id": "find_key",
                "status": "completed",
                "objectives": [
                    {"id": "key", "text": "Recupera la chiave", "done": True},
                ],
            }],
            8,
        )
        self.assertEqual(active_quests(extra), [])
        self.assertEqual(extra["quests"][0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()

    def test_turn_without_active_campaign_does_not_advance_world(self):
        from app.story_chat import story_turn

        character = {
            "id": 17,
            "identity": object(),
            "languages": [],
            "extra": {"campaign": {"started": False}, "game_state": {"turn": 4}},
        }
        with patch("app.story_chat.get_character", return_value=character), \
             patch("app.story_chat.advance_turn") as advance_turn_mock, \
             patch("app.story_chat.advance_world") as advance_world_mock:
            with self.assertRaisesRegex(ValueError, "Nessuna storia attiva"):
                story_turn(17, "Guardo la stanza.")

        advance_turn_mock.assert_not_called()
        advance_world_mock.assert_not_called()
        self.assertEqual(character["extra"]["game_state"]["turn"], 4)

