from __future__ import annotations

import json
import re
from typing import Any

from app.ai_provider import ask_ollama
from app.database.characters_db import get_character


def _character_payload(character: dict[str, Any]) -> dict[str, Any]:
    identity = character.get("identity")
    extra = character.get("extra") if isinstance(character.get("extra"), dict) else {}
    if identity is None:
        raise ValueError("Personaggio privo di identità.")
    return {
        "id": character.get("id"),
        "name": identity.name,
        "surname": identity.surname,
        "nickname": identity.nickname,
        "age": identity.age,
        "sex": identity.sex,
        "race": identity.race,
        "physical_description": identity.physical_description,
        "appearance": identity.appearance,
        "psychology": extra.get("psychology", {}),
        "personality": extra.get("personality", {}),
        "statistics": extra.get("statistics", {}),
        "abilities": extra.get("abilities", []),
        "skills": extra.get("skills", []),
        "conditions": extra.get("conditions", {}),
        "inventory": extra.get("inventory", {}),
        "magic": extra.get("magic", {}),
    }


def _extract_json(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("L'IA dello scontro ha restituito una risposta vuota.")

    # Qwen può occasionalmente restituire blocchi markdown anche quando viene
    # richiesto JSON. Rimuoviamo solo il contenitore, senza alterare il JSON.
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text).strip()

    # Se il modello ha aggiunto testo prima/dopo l'oggetto, recuperiamo il primo
    # oggetto JSON bilanciato rispettando stringhe ed escape.
    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    if start < 0:
        raise ValueError(f"L'IA dello scontro non ha restituito un oggetto JSON: {text[:500]}")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    raise ValueError(f"L'IA dello scontro ha restituito JSON incompleto: {text[:500]}")


def _parse_result(raw: str) -> dict[str, Any]:
    extracted = _extract_json(raw)
    try:
        result = json.loads(extracted)
    except json.JSONDecodeError as error:
        raise ValueError(
            "L'IA dello scontro ha restituito JSON non valido. "
            f"Risposta ricevuta: {extracted[:1000]}"
        ) from error
    if not isinstance(result, dict):
        raise ValueError("Il risultato dello scontro deve essere un oggetto JSON.")
    if not isinstance(result.get("rounds"), list):
        raise ValueError("Lo scontro non contiene i round.")
    if not isinstance(result.get("winner"), str):
        raise ValueError("Lo scontro non contiene un vincitore valido.")
    return result


def simulate_battle(character_a_id: int, character_b_id: int, style: str = "cinematico") -> dict[str, Any]:
    if not isinstance(character_a_id, int) or isinstance(character_a_id, bool):
        raise ValueError("ID del primo combattente non valido.")
    if not isinstance(character_b_id, int) or isinstance(character_b_id, bool):
        raise ValueError("ID del secondo combattente non valido.")
    if character_a_id == character_b_id:
        raise ValueError("Devi selezionare due personaggi diversi.")

    a = get_character(character_a_id)
    b = get_character(character_b_id)
    if a is None or b is None:
        raise ValueError("Uno dei due personaggi non esiste.")

    fighter_a = _character_payload(a)
    fighter_b = _character_payload(b)
    requested_style = str(style or "cinematico").strip() or "cinematico"

    system_prompt = """
Sei il direttore di uno scontro fantasy per un GDR narrativo.
Devi simulare l'intero combattimento tra DUE personaggi già esistenti.
Non devi creare nuovi personaggi, nuove abilità arbitrarie o statistiche non presenti.
Usa identità, personalità, psicologia, statistiche, abilità, skill, condizioni, inventario e magie forniti.
Le capacità devono essere usate in modo coerente con i dati reali del personaggio.
Non favorire automaticamente il primo o il più potente: valuta tattica, terreno, personalità, errori, fortuna narrativa plausibile e condizioni.
Lo scontro deve avere un inizio, sviluppo, svolte e conclusione. Può essere breve o lungo, ma deve sembrare una scena completa di GDR.
I personaggi possono subire ferite, stanchezza, paura, esitazioni e conseguenze coerenti. Non uccidere un personaggio senza che lo scontro lo giustifichi.
Non modificare il database: questa è una simulazione narrativa autonoma.

REGOLE JSON:
- Restituisci SOLO un singolo oggetto JSON.
- Non usare markdown, non usare ``` e non aggiungere spiegazioni prima o dopo il JSON.
- Tutti i valori testuali devono essere stringhe JSON valide.
- Non inserire virgolette non escapate dentro le stringhe.
- Non lasciare commenti o trailing commas.
""".strip()

    user_prompt = f"""
COMBATTENTE A:
{json.dumps(fighter_a, ensure_ascii=False, indent=2, default=str)}

COMBATTENTE B:
{json.dumps(fighter_b, ensure_ascii=False, indent=2, default=str)}

STILE RICHIESTO: {requested_style}

Genera lo scontro completo.
Usa esattamente questa struttura JSON:
{{
  "title": "titolo breve dello scontro",
  "introduction": "contesto e inizio dello scontro",
  "rounds": [
    {{
      "round": 1,
      "narration": "narrazione completa del round",
      "events": ["evento 1", "evento 2"],
      "status": {{"fighter_a": "stato sintetico", "fighter_b": "stato sintetico"}}
    }}
  ],
  "winner": "nome del vincitore oppure Pareggio",
  "ending": "conclusione dello scontro",
  "aftermath": "conseguenze immediate per entrambi"
}}
""".strip()

    result = _parse_result(ask_ollama(system_prompt, user_prompt))
    result["fighters"] = [fighter_a, fighter_b]
    return result
