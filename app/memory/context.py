from __future__ import annotations

from typing import Any


def build_continuity_facts(memories: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[str]:
    """Return explicit facts the character is allowed to treat as real."""
    facts: list[str] = []

    for memory in memories:
        content = memory.get("content") if isinstance(memory, dict) else None
        if isinstance(content, str) and content.strip():
            facts.append(f"MEMORIA: {content.strip()}")

    for event in events:
        if not isinstance(event, dict):
            continue
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            continue

        player = payload.get("player")
        character = payload.get("character")
        if isinstance(player, str) and player.strip():
            facts.append(f"EVENTO - Il giocatore ha detto: {player.strip()}")
        if isinstance(character, str) and character.strip():
            facts.append(f"EVENTO - {character.strip()}")

        actions = payload.get("actions", [])
        if isinstance(actions, list):
            for action in actions:
                if not isinstance(action, dict):
                    continue
                action_type = action.get("type")
                if action_type == "world_action":
                    facts.append(f"EVENTO - Azione del personaggio: {action}")
                elif action_type == "relationship_change":
                    facts.append(f"EVENTO - Cambiamento relazione: {action}")
                elif action_type == "create_memory":
                    content = action.get("content")
                    if isinstance(content, str) and content.strip():
                        facts.append(f"EVENTO - Memoria creata: {content.strip()}")

    # Evita di gonfiare inutilmente il prompt mantenendo l'ordine cronologico.
    return facts[-80:]
