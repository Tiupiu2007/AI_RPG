from __future__ import annotations

from typing import Any


MAX_QUESTS = 100
MAX_OBJECTIVES = 20


def ensure_quests(extra: dict[str, Any]) -> list[dict[str, Any]]:
    quests = extra.get("quests")
    if not isinstance(quests, list):
        quests = []
        extra["quests"] = quests
    return quests


def _quest_id(value: Any) -> str:
    value = str(value or "").strip()
    if not value or len(value) > 120:
        raise ValueError("quest_id non valido.")
    return value


def apply_quest_updates(
    extra: dict[str, Any],
    updates: list[dict[str, Any]],
    current_turn: int,
) -> list[dict[str, Any]]:
    """Applica aggiornamenti quest persistenti proposti dalla narrazione."""
    if not isinstance(updates, list):
        return []

    quests = ensure_quests(extra)
    index = {
        str(q.get("id")): q
        for q in quests
        if isinstance(q, dict) and q.get("id") is not None
    }

    changed: list[dict[str, Any]] = []
    for raw in updates[:8]:
        if not isinstance(raw, dict):
            continue
        qid = raw.get("id")
        if not isinstance(qid, str) or not qid.strip():
            continue
        qid = _quest_id(qid)

        title = raw.get("title")
        description = raw.get("description")
        status = raw.get("status", "active")
        if status not in {"active", "completed", "failed", "paused"}:
            continue

        if qid in index:
            quest = index[qid]
        else:
            if len(quests) >= MAX_QUESTS:
                continue
            if not isinstance(title, str) or not title.strip():
                continue
            quest = {
                "id": qid,
                "title": title.strip()[:160],
                "description": str(description or "").strip()[:500],
                "status": "active",
                "objectives": [],
                "created_turn": current_turn,
            }
            quests.append(quest)
            index[qid] = quest

        if isinstance(title, str) and title.strip():
            quest["title"] = title.strip()[:160]
        if isinstance(description, str):
            quest["description"] = description.strip()[:500]

        objectives = raw.get("objectives")
        if isinstance(objectives, list):
            normalized = []
            for objective in objectives[:MAX_OBJECTIVES]:
                if not isinstance(objective, dict):
                    continue
                oid = objective.get("id")
                text = objective.get("text")
                if not isinstance(oid, str) or not oid.strip() or not isinstance(text, str) or not text.strip():
                    continue
                normalized.append({
                    "id": oid.strip()[:120],
                    "text": text.strip()[:300],
                    "done": bool(objective.get("done", False)),
                })
            if normalized:
                quest["objectives"] = normalized

        quest["status"] = status
        quest["updated_turn"] = current_turn
        changed.append(dict(quest))

    # Le quest completate/fallite restano nello storico ma non possono crescere
    # all'infinito: conserviamo le più recenti.
    if len(quests) > MAX_QUESTS:
        quests[:] = quests[-MAX_QUESTS:]
    return changed


def active_quests(extra: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        q for q in ensure_quests(extra)
        if isinstance(q, dict) and q.get("status") == "active"
    ]
