from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any


CARDS_FILE = Path(__file__).resolve().parents[2] / "frontend" / "cards-data.json"
_LOCK = RLock()


class CardError(ValueError):
    pass


def _read_raw_cards() -> list[dict[str, Any]]:
    if not CARDS_FILE.exists():
        return []
    try:
        data = json.loads(CARDS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CardError(f"Catalogo carte non valido: {exc}") from exc
    if not isinstance(data, list):
        raise CardError("Il catalogo delle carte deve essere una lista JSON.")
    return [card for card in data if isinstance(card, dict)]


def _write_raw_cards(cards: list[dict[str, Any]]) -> None:
    CARDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CARDS_FILE.write_text(
        json.dumps(cards, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_cards() -> list[dict[str, Any]]:
    with _LOCK:
        return [normalize_card(card) for card in _read_raw_cards()]


def get_card(card_id: str) -> dict[str, Any] | None:
    card_id = str(card_id).strip()
    return next((card for card in load_cards() if card["id"] == card_id), None)


def upsert_card(card: dict[str, Any]) -> dict[str, Any]:
    """Create or replace a card. This function is intentionally server-side only."""
    normalized = normalize_card(card)
    with _LOCK:
        cards = _read_raw_cards()
        replaced = False
        for index, existing in enumerate(cards):
            if str(existing.get("id", "")).strip() == normalized["id"]:
                cards[index] = normalized
                replaced = True
                break
        if not replaced:
            cards.append(normalized)
        _write_raw_cards(cards)
    return normalized


def delete_card(card_id: str) -> bool:
    card_id = str(card_id).strip()
    if not card_id:
        raise CardError("ID carta mancante.")
    with _LOCK:
        cards = _read_raw_cards()
        filtered = [card for card in cards if str(card.get("id", "")).strip() != card_id]
        if len(filtered) == len(cards):
            return False
        _write_raw_cards(filtered)
    return True


def normalize_card(card: dict[str, Any]) -> dict[str, Any]:
    card_id = str(card.get("id", "")).strip()
    name = str(card.get("name", "")).strip()
    if not card_id or not name:
        raise CardError("Ogni carta deve avere almeno 'id' e 'name'.")

    requirements = card.get("requirements", {})
    if not isinstance(requirements, dict):
        requirements = {}
    statistics = requirements.get("statistics", {})
    if not isinstance(statistics, dict):
        statistics = {}

    resource = str(card.get("resource", "action_points")).strip() or "action_points"
    cost = max(0, _int(card.get("cost", 1), 1))
    mana_cost = max(0, _int(card.get("mana_cost", cost if resource == "mana" else 0), 0))
    action_points_cost = max(0, _int(card.get("action_points_cost", 1 if resource == "mana" else cost), 1))

    return {
        "id": card_id,
        "name": name,
        "type": str(card.get("type", "skill")).strip() or "skill",
        "rarity": str(card.get("rarity", "common")).strip() or "common",
        "cost": cost,
        "resource": resource,
        "mana_cost": mana_cost,
        "action_points_cost": action_points_cost,
        "target": str(card.get("target", "enemy")).strip() or "enemy",
        "description": str(card.get("description", "")).strip(),
        "flavor": str(card.get("flavor", "")).strip(),
        "image": str(card.get("image", "")).strip(),
        "exhaust": bool(card.get("exhaust", False)),
        "requirements": {
            "statistics": {str(key): _int(value, 0) for key, value in statistics.items()},
            "races": _string_list(requirements.get("races", [])),
            "tags": _string_list(requirements.get("tags", [])),
            "requires_cards": _string_list(requirements.get("requires_cards", [])),
            "min_level": max(1, _int(requirements.get("min_level", 1), 1)),
        },
        "effects": card.get("effects", []) if isinstance(card.get("effects", []), list) else [],
        "tags": _string_list(card.get("tags", [])),
    }


def can_learn_card(card: dict[str, Any], character: dict[str, Any]) -> tuple[bool, list[str]]:
    card = normalize_card(card)
    extra = character.get("extra", {}) if isinstance(character, dict) else {}
    if not isinstance(extra, dict):
        extra = {}
    identity = character.get("identity", {}) if isinstance(character, dict) else {}
    if not isinstance(identity, dict):
        identity = {}
    stats = extra.get("statistics", {})
    if not isinstance(stats, dict):
        stats = {}
    requirements = card["requirements"]
    reasons: list[str] = []

    for stat, minimum in requirements["statistics"].items():
        try:
            value = float(stats.get(stat, 0))
        except (TypeError, ValueError):
            value = 0
        if value < minimum:
            reasons.append(f"{stat} >= {minimum}")

    race = str(identity.get("race", "")).strip().lower()
    allowed_races = {item.lower() for item in requirements["races"]}
    if allowed_races and race not in allowed_races:
        reasons.append("razza richiesta: " + ", ".join(requirements["races"]))

    level = _int(extra.get("level", 1), 1)
    if level < requirements["min_level"]:
        reasons.append(f"livello >= {requirements['min_level']}")

    character_tags = {str(x).strip().lower() for x in _string_list(extra.get("tags", []))}
    for required_tag in requirements["tags"]:
        if required_tag.lower() not in character_tags:
            reasons.append(f"tag richiesto: {required_tag}")

    known = extra.get("cards", extra.get("deck", []))
    if not isinstance(known, list):
        known = []
    known_ids = set()
    for item in known:
        if isinstance(item, dict) and item.get("id"):
            known_ids.add(str(item["id"]))
        elif isinstance(item, str):
            known_ids.add(item.strip())
    for required in requirements["requires_cards"]:
        if required not in known_ids:
            reasons.append(f"richiede la carta: {required}")

    return not reasons, reasons


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
