from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CARDS_FILE = Path(__file__).resolve().parents[2] / "frontend" / "cards-data.json"


class CardError(ValueError):
    pass


def load_cards() -> list[dict[str, Any]]:
    if not CARDS_FILE.exists():
        return []
    try:
        data = json.loads(CARDS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CardError(f"Catalogo carte non valido: {exc}") from exc
    if not isinstance(data, list):
        raise CardError("Il catalogo delle carte deve essere una lista JSON.")
    return [normalize_card(card) for card in data if isinstance(card, dict)]


def get_card(card_id: str) -> dict[str, Any] | None:
    card_id = str(card_id).strip()
    return next((card for card in load_cards() if card["id"] == card_id), None)


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

    return {
        "id": card_id,
        "name": name,
        "type": str(card.get("type", "skill")).strip() or "skill",
        "rarity": str(card.get("rarity", "common")).strip() or "common",
        "cost": max(0, _int(card.get("cost", 1), 1)),
        "resource": str(card.get("resource", "action_points")).strip() or "action_points",
        "description": str(card.get("description", "")).strip(),
        "flavor": str(card.get("flavor", "")).strip(),
        "image": str(card.get("image", "")).strip(),
        "requirements": {
            "statistics": {str(key): _int(value, 0) for key, value in statistics.items()},
            "races": _string_list(requirements.get("races", [])),
            "tags": _string_list(requirements.get("tags", [])),
            "requires_cards": _string_list(requirements.get("requires_cards", [])),
            "min_level": max(0, _int(requirements.get("min_level", 1), 1)),
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

    known = extra.get("cards", [])
    if not isinstance(known, list):
        known = []
    known_ids = {str(item.get("id" if isinstance(item, dict) else "", item) if isinstance(item, (dict, str)) else "") for item in known}
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
