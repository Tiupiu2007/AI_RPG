from __future__ import annotations

from typing import Any


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.strip().split())
    return value or None


def _belongs_to_character(item: dict[str, Any], character_id: int) -> bool:
    """Accetta solo dati esplicitamente appartenenti al personaggio corrente."""
    owner = item.get("character_id")
    return isinstance(owner, int) and not isinstance(owner, bool) and owner == character_id


def build_continuity_facts(
    memories: list[dict[str, Any]],
    events: list[dict[str, Any]],
    character_id: int | None = None,
) -> list[str]:
    """Costruisce fatti che il personaggio corrente è autorizzato a conoscere.

    La continuità è volutamente separata per personaggio. Se viene fornito
    character_id, qualsiasi memoria/evento con un proprietario diverso viene
    scartato prima di entrare nel prompt AI.
    """
    facts: list[str] = []

    for memory in memories:
        if not isinstance(memory, dict):
            continue
        if character_id is not None and not _belongs_to_character(memory, character_id):
            continue
        content = _clean_text(memory.get("content"))
        if content:
            facts.append(f"MEMORIA DEL PERSONAGGIO CORRENTE: {content}")

    for event in events:
        if not isinstance(event, dict):
            continue
        if character_id is not None and not _belongs_to_character(event, character_id):
            continue

        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            continue

        player = _clean_text(payload.get("player"))
        character = _clean_text(payload.get("character"))
        if player:
            facts.append(f"EVENTO DEL PERSONAGGIO CORRENTE - Il PLAYER ha detto: {player}")
        if character:
            facts.append(f"EVENTO DEL PERSONAGGIO CORRENTE - Risposta di questo personaggio: {character}")

        actions = payload.get("actions", [])
        if not isinstance(actions, list):
            continue

        for action in actions:
            if not isinstance(action, dict):
                continue

            action_type = action.get("type")
            if action_type == "world_action":
                facts.append(
                    "EVENTO DEL PERSONAGGIO CORRENTE - Azione del personaggio: "
                    f"{action}"
                )
            elif action_type == "relationship_change":
                facts.append(
                    "EVENTO DEL PERSONAGGIO CORRENTE - Cambiamento relazione: "
                    f"{action}"
                )
            elif action_type == "create_memory":
                content = _clean_text(action.get("content"))
                if content:
                    facts.append(
                        "EVENTO DEL PERSONAGGIO CORRENTE - Memoria creata: "
                        f"{content}"
                    )

    # Mantiene l'ordine cronologico e limita il prompt.
    return facts[-80:]
