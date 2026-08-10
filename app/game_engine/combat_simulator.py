from __future__ import annotations

import json
from typing import Any

from app.ai_provider import ask_ollama
from app.database.characters_db import get_character


def _clean_character(character: dict[str, Any]) -> dict[str, Any]:
    identity = character.get("identity")
    if not isinstance(identity, dict):
        identity = {}
    extra = character.get("extra")
    if not isinstance(extra, dict):
        extra = {}
    return {
        "id": character.get("id"),
        "identity": identity,
        "languages": character.get("languages", []),
        "psychology": extra.get("psychology", {}),
        "personality": extra.get("personality", {}),
        "statistics": extra.get("statistics", {}),
        "abilities": extra.get("abilities", []),
        "skills": extra.get("skills", []),
        "conditions": extra.get("conditions", {}),
        "inventory": extra.get("inventory", {}),
        "magic": extra.get("magic", {}),
    }


def simulate_combat(character_a_id: int, character_b_id: int) -> dict[str, Any]:
    if character_a_id == character_b_id:
        raise ValueError("Uno scontro richiede due personaggi diversi.")
    a = get_character(character_a_id)
    b = get_character(character_b_id)
    if a is None or b is None:
        raise ValueError("Uno dei personaggi selezionati non esiste.")

    ca = _clean_character(a)
    cb = _clean_character(b)
    name_a = ca["identity"].get("name") or f"Personaggio {character_a_id}"
    surname_a = ca["identity"].get("surname") or ""
    name_b = cb["identity"].get("name") or f"Personaggio {character_b_id}"
    surname_b = cb["identity"].get("surname") or ""
    full_a = f"{name_a} {surname_a}".strip()
    full_b = f"{name_b} {surname_b}".strip()

    prompt = f"""
Sei il direttore di un GDR narrativo. Devi simulare interamente uno scontro tra due personaggi.

PERSONAGGIO A:
{json.dumps(ca, ensure_ascii=False, indent=2, default=str)}

PERSONAGGIO B:
{json.dumps(cb, ensure_ascii=False, indent=2, default=str)}

REGOLE:
- Usa esclusivamente le informazioni fornite.
- Non inventare poteri, magie, oggetti o statistiche che non esistono nel profilo.
- Considera statistiche, condizioni, abilità, skill, magie, equipaggiamento e comportamento.
- La personalità deve influenzare tattica e decisioni.
- Un personaggio molto più forte può vincere facilmente.
- Un personaggio più debole può vincere se ha un vantaggio tattico realmente presente.
- Non forzare un pareggio e non favorire nessuno.
- Racconta lo scontro dall'inizio alla fine, con azioni comprensibili e conseguenze coerenti.
- Puoi usare più round, ma evita lungaggini inutili.
- Determina un vincitore reale quando uno dei due prevale.
- Questa è SOLO una simulazione: non modificare database, condizioni, inventario, memoria, relazioni o storia.
- Non controllare il giocatore: entrambi sono personaggi autonomi della simulazione.

Restituisci esclusivamente JSON valido:
{{
  "winner_id": 0,
  "loser_id": 0,
  "rounds": [
    {{"round": 1, "events": ["evento narrativo"]}}
  ],
  "summary": "breve conclusione dello scontro",
  "narration": "narrazione completa dello scontro"
}}
""".strip()

    raw = ask_ollama("Sei un arbitro imparziale di un GDR. Rispondi solo JSON valido.", prompt)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("L'IA ha restituito una simulazione non valida.") from exc
    if not isinstance(result, dict):
        raise ValueError("La simulazione deve essere un oggetto JSON.")

    winner_id = result.get("winner_id")
    if winner_id not in (character_a_id, character_b_id):
        raise ValueError("L'IA non ha determinato un vincitore valido.")
    result["winner_id"] = winner_id
    result["loser_id"] = character_b_id if winner_id == character_a_id else character_a_id
    result["winner_name"] = full_a if winner_id == character_a_id else full_b
    result["participants"] = {"a": full_a, "b": full_b}
    return result
