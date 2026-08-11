from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

from app.combat.cards import can_learn_card, load_cards

DECKS_FILE = Path(__file__).resolve().parents[2] / "data" / "pvp_decks.json"
_LOCK = RLock()


def _load() -> dict[str, Any]:
    if not DECKS_FILE.exists():
        return {}
    try:
        data = json.loads(DECKS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict[str, Any]) -> None:
    DECKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DECKS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        card_id = item.get("id") if isinstance(item, dict) else item
        if card_id:
            card_id = str(card_id).strip()
            if card_id and card_id not in result:
                result.append(card_id)
    return result


def get_deck(character_id: int) -> dict[str, list[str]]:
    with _LOCK:
        data = _load()
        entry = data.get(str(character_id), {})
        if not isinstance(entry, dict):
            entry = {}
        known = _ids(entry.get("known", []))
        deck = _ids(entry.get("deck", []))
        return {"known": known, "deck": deck}


def _character_tags(character: dict[str, Any]) -> set[str]:
    extra = character.get("extra", {}) if isinstance(character, dict) else {}
    if not isinstance(extra, dict):
        return set()
    raw = extra.get("tags", [])
    return {str(x).strip().lower() for x in raw} if isinstance(raw, list) else set()


def get_card_catalog_for_character(character: dict[str, Any]) -> list[dict[str, Any]]:
    deck_state = get_deck(int(character["id"]))
    known = set(deck_state["known"])
    current_deck = set(deck_state["deck"])
    cards: list[dict[str, Any]] = []
    for card in load_cards():
        learnable, reasons = can_learn_card(card, character)
        item = dict(card)
        item["learnable"] = learnable
        item["blocked_reasons"] = reasons
        item["known"] = card["id"] in known
        item["in_deck"] = card["id"] in current_deck
        cards.append(item)
    return cards


def learn_card(character: dict[str, Any], card_id: str) -> dict[str, list[str]]:
    card_id = str(card_id).strip()
    card = next((x for x in load_cards() if x["id"] == card_id), None)
    if card is None:
        raise ValueError("Carta non trovata nel catalogo.")
    learnable, reasons = can_learn_card(card, character)
    if not learnable:
        raise ValueError("Non puoi imparare questa carta: " + ", ".join(reasons))
    with _LOCK:
        data = _load()
        entry = data.setdefault(str(character["id"]), {"known": [], "deck": []})
        known = _ids(entry.get("known", []))
        if card_id not in known:
            known.append(card_id)
        entry["known"] = known
        entry["deck"] = _ids(entry.get("deck", []))
        _save(data)
        return {"known": known, "deck": entry["deck"]}


def forget_card(character_id: int, card_id: str) -> dict[str, list[str]]:
    card_id = str(card_id).strip()
    with _LOCK:
        data = _load()
        entry = data.setdefault(str(character_id), {"known": [], "deck": []})
        entry["known"] = [x for x in _ids(entry.get("known", [])) if x != card_id]
        entry["deck"] = [x for x in _ids(entry.get("deck", [])) if x != card_id]
        _save(data)
        return {"known": entry["known"], "deck": entry["deck"]}


def toggle_deck_card(character: dict[str, Any], card_id: str) -> dict[str, list[str]]:
    card_id = str(card_id).strip()
    catalog = {x["id"]: x for x in load_cards()}
    if card_id not in catalog:
        raise ValueError("Carta non trovata nel catalogo.")
    learnable, reasons = can_learn_card(catalog[card_id], character)
    if not learnable:
        raise ValueError("Carta bloccata: " + ", ".join(reasons))
    with _LOCK:
        data = _load()
        entry = data.setdefault(str(character["id"]), {"known": [], "deck": []})
        known = _ids(entry.get("known", []))
        deck = _ids(entry.get("deck", []))
        if card_id not in known:
            known.append(card_id)
        if card_id in deck:
            deck.remove(card_id)
        else:
            deck.append(card_id)
        entry["known"] = known
        entry["deck"] = deck
        _save(data)
        return {"known": known, "deck": deck}
