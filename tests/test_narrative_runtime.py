import unittest

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
