from __future__ import annotations

import json
import random
import re
from typing import Any

from app.ai_provider import ask_ollama
from app.combat.combat_engine import create_combat, resolve_round
from app.combat.combat_models import CombatState
from app.database.characters_db import get_character

MAX_ROUNDS = 40
MAX_ACTION_RETRIES = 2


def _fighter(character: dict[str, Any]) -> dict[str, Any]:
    identity = character["identity"]
    extra = character.get("extra", {}) if isinstance(character.get("extra"), dict) else {}
    return {
        "id": character["id"], "name": identity.name, "surname": identity.surname,
        "nickname": identity.nickname, "race": identity.race,
        "physical_description": identity.physical_description, "appearance": identity.appearance,
        "psychology": extra.get("psychology", {}), "personality": extra.get("personality", {}),
        "statistics": extra.get("statistics", {}), "abilities": extra.get("abilities", []),
        "skills": extra.get("skills", []), "conditions": extra.get("conditions", {}),
        "inventory": extra.get("inventory", {}), "magic": extra.get("magic", {}),
    }


def _json_object(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text).strip()
    start = text.find("{")
    if start < 0:
        raise ValueError(f"L'IA non ha restituito JSON: {text[:500]}")
    depth = 0
    quoted = False
    escaped = False
    for i in range(start, len(text)):
        c = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    result = json.loads(text[start:i + 1])
                except json.JSONDecodeError as error:
                    raise ValueError(f"JSON IA non valido: {text[start:i + 1][:1000]}") from error
                if not isinstance(result, dict):
                    raise ValueError("Il JSON IA deve essere un oggetto.")
                return result
    raise ValueError("JSON IA incompleto.")


def _choose_actions(state: CombatState, a: dict[str, Any], b: dict[str, Any], style: str) -> list[dict[str, Any]]:
    system = "Sei un arbitro tattico di un GDR. Restituisci esclusivamente JSON valido. Non decidere danni o risultati."
    prompt = f"""
Decidi la prossima intenzione di entrambi i combattenti.
Azioni consentite: attack, ability, defend, recover, flee, wait, observe, taunt, speak.
Per attack/ability indica il bersaglio. Usa solo abilità realmente presenti.
Non inventare statistiche, poteri o oggetti. Un'azione per personaggio.

A:
{json.dumps(a, ensure_ascii=False, indent=2, default=str)}
B:
{json.dumps(b, ensure_ascii=False, indent=2, default=str)}
Stile: {style}
Stato motore:
{json.dumps(state.to_dict(), ensure_ascii=False, indent=2, default=str)}

Rispondi SOLO:
{{"actions":[
{{"character_id":{a['id']},"action":"attack","target_id":{b['id']},"ability":null,"description":"intenzione breve","intent":"motivo breve"}},
{{"character_id":{b['id']},"action":"attack","target_id":{a['id']},"ability":null,"description":"intenzione breve","intent":"motivo breve"}}
]}}
""".strip()
    for attempt in range(MAX_ACTION_RETRIES + 1):
        try:
            result = _json_object(ask_ollama(system, prompt))
            raw_actions = result.get("actions")
            if not isinstance(raw_actions, list):
                raise ValueError("actions mancante")
            normalized: dict[int, dict[str, Any]] = {}
            allowed = {"attack", "ability", "defend", "recover", "flee", "wait", "observe", "taunt", "speak"}
            for raw in raw_actions:
                if not isinstance(raw, dict):
                    continue
                cid = raw.get("character_id")
                if cid not in {a["id"], b["id"]} or cid in normalized:
                    continue
                action = str(raw.get("action", "wait")).lower().strip()
                if action not in allowed:
                    action = "wait"
                normalized[cid] = {
                    "character_id": cid, "action": action,
                    "target_id": (b["id"] if cid == a["id"] else a["id"]) if action in {"attack", "ability"} else None,
                    "ability": raw.get("ability"), "description": str(raw.get("description", ""))[:1000],
                    "intent": str(raw.get("intent", ""))[:500],
                }
            normalized.setdefault(a["id"], {"character_id": a["id"], "action": "wait", "target_id": None, "description": "Attende.", "intent": "Nessuna azione valida."})
            normalized.setdefault(b["id"], {"character_id": b["id"], "action": "wait", "target_id": None, "description": "Attende.", "intent": "Nessuna azione valida."})
            return [normalized[a["id"]], normalized[b["id"]]]
        except ValueError as error:
            if attempt == MAX_ACTION_RETRIES:
                raise
            prompt += "\nLa risposta precedente era invalida. Restituisci esclusivamente JSON valido."
    raise RuntimeError("Impossibile scegliere le azioni.")


def _narrate(state: CombatState, a: dict[str, Any], b: dict[str, Any], style: str) -> dict[str, Any]:
    system = "Sei il narratore di un GDR fantasy. Usa esclusivamente eventi reali del motore. Non alterare il vincitore o i danni. Solo JSON valido."
    prompt = f"""
Racconta in modo cinematografico ma coerente questo combattimento.
Stile: {style}
A: {json.dumps(a, ensure_ascii=False, default=str)}
B: {json.dumps(b, ensure_ascii=False, default=str)}
Eventi reali:
{json.dumps([e.to_dict() for e in state.events], ensure_ascii=False, indent=2, default=str)}
Stato finale:
{json.dumps(state.to_dict(), ensure_ascii=False, indent=2, default=str)}

Formato:
{{"title":"titolo","introduction":"inizio","rounds":[{{"round":1,"narration":"narrazione","events":["evento"]}}],"winner":"vincitore o Pareggio","ending":"conclusione","aftermath":"conseguenze"}}
""".strip()
    result = _json_object(ask_ollama(system, prompt))
    if not isinstance(result.get("rounds"), list):
        result["rounds"] = []
    return result


def simulate_battle(character_a_id: int, character_b_id: int, style: str = "cinematico", *, seed: int | None = None, max_rounds: int = MAX_ROUNDS) -> dict[str, Any]:
    if not isinstance(character_a_id, int) or isinstance(character_a_id, bool) or not isinstance(character_b_id, int) or isinstance(character_b_id, bool):
        raise ValueError("ID combattente non valido.")
    if character_a_id == character_b_id:
        raise ValueError("Devi selezionare due personaggi diversi.")
    if max_rounds <= 0:
        raise ValueError("max_rounds deve essere maggiore di zero.")
    a_db, b_db = get_character(character_a_id), get_character(character_b_id)
    if a_db is None or b_db is None:
        raise ValueError("Uno dei due personaggi non esiste.")
    a, b = _fighter(a_db), _fighter(b_db)
    style = str(style or "cinematico").strip() or "cinematico"
    rng_seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    state = create_combat([a_db, b_db], seed=rng_seed, metadata={"style": style, "ai_directed": True})
    action_history = []
    for index in range(max_rounds):
        if state.phase != "active":
            break
        actions = _choose_actions(state, a, b, style)
        action_history.append({"round": state.round_number, "actions": actions})
        resolve_round(state, actions, seed=rng_seed + index)
    if state.phase == "active":
        state.phase = "draw"
        state.add_event("combat_end", "Lo scontro termina senza vincitore entro il limite di round.")
    narrative = _narrate(state, a, b, style)
    winner_name = "Pareggio" if state.winner_id is None else state.get_combatant(state.winner_id).name
    return {**narrative, "winner": winner_name, "winner_id": state.winner_id, "combat": state.to_dict(), "action_history": action_history, "fighters": [a, b]}
