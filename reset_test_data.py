"""Reset controllato dei dati temporanei usati durante i test dell'AI RPG.

NON elimina i personaggi, le identità, le lingue, le statistiche o la configurazione.
Cancella soltanto:
- memorie persistenti;
- eventi persistenti;
- cronologia conversazionale salvata in extra_data.

Uso:
    python reset_test_data.py

Per sicurezza richiede una conferma esplicita prima di modificare il database.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.database.characters_db import get_connection, init_database


DATABASE_PATH = Path("data/characters.db")


def reset_test_data() -> dict[str, int]:
    """Cancella esclusivamente i dati temporanei del sistema di test."""
    init_database()
    connection = get_connection()
    try:
        memory_count = int(connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
        event_count = int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])

        conversation_count = 0
        rows = connection.execute("SELECT id, extra_data FROM characters").fetchall()
        for row in rows:
            try:
                extra = json.loads(row["extra_data"] or "{}")
            except (TypeError, json.JSONDecodeError):
                extra = {}

            if not isinstance(extra, dict):
                extra = {}

            conversation = extra.pop("conversation", None)
            if isinstance(conversation, list) and conversation:
                conversation_count += 1

            connection.execute(
                "UPDATE characters SET extra_data = ? WHERE id = ?",
                (json.dumps(extra, ensure_ascii=False), row["id"]),
            )

        connection.execute("DELETE FROM memories")
        connection.execute("DELETE FROM events")
        connection.commit()

        character_count = int(connection.execute("SELECT COUNT(*) FROM characters").fetchone()[0])
        return {
            "characters_preserved": character_count,
            "memories_deleted": memory_count,
            "events_deleted": event_count,
            "conversations_cleared": conversation_count,
        }
    finally:
        connection.close()


def main() -> None:
    print("=" * 60)
    print("AI RPG - RESET DATI DI TEST")
    print("=" * 60)
    print(f"Database: {DATABASE_PATH.resolve()}")
    print()
    print("Verranno cancellati SOLO:")
    print("  - memorie")
    print("  - eventi")
    print("  - cronologia conversazioni")
    print()
    print("I personaggi e le loro identità NON verranno eliminati.")
    print()

    confirmation = input("Scrivi RESET per continuare: ").strip()
    if confirmation != "RESET":
        print("Operazione annullata.")
        return

    result = reset_test_data()
    print()
    print("Reset completato.")
    print(f"Personaggi mantenuti: {result['characters_preserved']}")
    print(f"Memorie eliminate: {result['memories_deleted']}")
    print(f"Eventi eliminati: {result['events_deleted']}")
    print(f"Conversazioni cancellate: {result['conversations_cleared']}")
    print()
    print("Ora puoi eseguire un test pulito di separazione delle memorie.")


if __name__ == "__main__":
    main()
