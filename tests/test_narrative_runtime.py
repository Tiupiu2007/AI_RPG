import unittest

from app.game_engine.quests import active_quests, apply_quest_updates


class NarrativeRuntimeTests(unittest.TestCase):
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
