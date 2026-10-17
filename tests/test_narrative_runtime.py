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


    def test_fallback_narration_reports_saved_action_without_inventing_outcomes(self):
        from app.story_chat import _fallback_narration

        rejected = _fallback_narration(
            {"type": "attack"},
            {"valid": False, "executed": False, "reason": "Bersaglio assente."},
        )
        self.assertIn("Bersaglio assente", rejected)

        moved = _fallback_narration(
            {"type": "move"},
            {
                "valid": True,
                "executed": True,
                "changes": {"location": {"to": "loc_taverna", "name": "Taverna"}},
            },
        )
        self.assertIn("Taverna", moved)

        generic = _fallback_narration(
            {"type": "none"},
            {"valid": True, "executed": True, "changes": {}},
        )
        self.assertIn("turno è stato salvato", generic)

    def test_social_updates_require_successful_talk_action(self):
        from app.story_chat import _social_update_matches_action

        action = {"type": "talk", "target_id": 22}
        update = {"character_id": 22, "social_effects": {"trust": 2}}

        self.assertTrue(
            _social_update_matches_action(
                action, {"valid": True, "executed": True}, update
            )
        )
        self.assertFalse(
            _social_update_matches_action(
                action, {"valid": False, "executed": False}, update
            )
        )
        self.assertFalse(
            _social_update_matches_action(
                action, {"valid": True, "executed": False}, update
            )
        )
        self.assertFalse(
            _social_update_matches_action(
                {"type": "inspect", "target_id": 22},
                {"valid": True, "executed": True},
                update,
            )
        )


    def test_full_turn_survives_narrator_failure_after_action_is_saved(self):
        import json
        from types import SimpleNamespace
        from app import story_chat

        character = {
            "id": 17,
            "identity": SimpleNamespace(name="Nox"),
            "languages": [],
            "extra": {"campaign": {"started": True}, "game_state": {"turn": 0}},
        }
        engine_result = {
            "valid": True,
            "executed": True,
            "action": {"type": "none", "target_id": None, "target_text": None, "parameters": {}},
            "changes": {},
        }
        with patch.object(story_chat, "get_character", return_value=character), \\
             patch.object(story_chat, "_build_context", return_value={}), \\
             patch.object(story_chat, "_build_system_prompt", return_value="intent prompt"), \\
             patch.object(story_chat, "_narration_prompt", return_value="narration prompt"), \\
             patch.object(story_chat, "ask_ollama", side_effect=[
                 json.dumps({"action": {"type": "none"}}),
                 RuntimeError("Ollama stopped"),
             ]), \\
             patch.object(story_chat, "advance_turn"), \\
             patch.object(story_chat, "advance_world", return_value=1), \\
             patch.object(story_chat, "execute_action", return_value=engine_result), \\
             patch.object(story_chat, "save_character") as save_mock, \\
             patch.object(story_chat, "record_world_event", return_value=101), \\
             patch.object(story_chat, "create_event", return_value=202), \\
             patch.object(story_chat, "_narration_needs_repair", return_value=False), \\
             patch("app.game_engine.progression.apply_progression", return_value=None):
            result = story_chat.story_turn(17, "Guardo la stanza.")

        self.assertIn("turno è stato salvato", result["narration"])
        self.assertEqual(len(result["action_options"]), 4)
        self.assertIn("\\n\\n1. **Prudente / razionale:**", result["narration"])
        self.assertEqual(len(character["extra"]["story_chat"]), 2)
        self.assertEqual(save_mock.call_count, 2)
        self.assertEqual(result["event_id"], 202)

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


if __name__ == "__main__":
    unittest.main()

    
