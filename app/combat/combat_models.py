from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Combat data model
# ---------------------------------------------------------------------------
# Questo modulo contiene SOLO dati e normalizzazione.
# Non decide chi vince, non tira dadi e non applica danni.
# La simulazione vera e propria appartiene a combat_engine.py.


@dataclass
class CombatantState:
    """Stato runtime di un combattente durante uno scontro."""

    character_id: int
    name: str
    health: int
    max_health: int
    stamina: int
    max_stamina: int
    mana: int
    max_mana: int
    statistics: dict[str, int] = field(default_factory=dict)
    abilities: list[dict[str, Any]] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)
    status: str = "Normale"
    alive: bool = True
    defeated: bool = False
    conditions: list[str] = field(default_factory=list)

    def clamp_resources(self) -> None:
        self.max_health = max(1, int(self.max_health))
        self.max_stamina = max(0, int(self.max_stamina))
        self.max_mana = max(0, int(self.max_mana))
        self.health = max(0, min(int(self.health), self.max_health))
        self.stamina = max(0, min(int(self.stamina), self.max_stamina))
        self.mana = max(0, min(int(self.mana), self.max_mana))
        self.alive = self.health > 0 and not self.defeated

    def to_dict(self) -> dict[str, Any]:
        self.clamp_resources()
        return asdict(self)


@dataclass
class CombatAction:
    """Intenzione di un combattente.

    È importante che questa struttura descriva l'intenzione e non il risultato.
    L'AI può proporre "attacco", ma non può decidere direttamente il danno.
    """

    character_id: int
    action: str
    target_id: int | None = None
    ability: str | None = None
    weapon: str | None = None
    description: str = ""
    intent: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CombatAction":
        if not isinstance(data, dict):
            raise ValueError("CombatAction deve essere un oggetto JSON.")

        character_id = data.get("character_id")
        if not isinstance(character_id, int) or isinstance(character_id, bool):
            raise ValueError("combat_action.character_id non valido.")

        action = data.get("action")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("combat_action.action non valido.")

        target_id = data.get("target_id")
        if target_id is not None and (not isinstance(target_id, int) or isinstance(target_id, bool)):
            raise ValueError("combat_action.target_id non valido.")

        return cls(
            character_id=character_id,
            action=action.strip().lower(),
            target_id=target_id,
            ability=_optional_text(data.get("ability")),
            weapon=_optional_text(data.get("weapon")),
            description=_bounded_text(data.get("description", ""), 1000),
            intent=_bounded_text(data.get("intent", ""), 500),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CombatEvent:
    """Singolo evento prodotto dalla simulazione."""

    round_number: int
    actor_id: int | None
    target_id: int | None
    event_type: str
    description: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CombatState:
    """Stato completo e serializzabile di uno scontro."""

    combat_id: str
    round_number: int = 1
    phase: str = "active"
    combatants: dict[int, CombatantState] = field(default_factory=dict)
    turn_order: list[int] = field(default_factory=list)
    events: list[CombatEvent] = field(default_factory=list)
    winner_id: int | None = None
    loser_ids: list[int] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_combatant(self, character_id: int) -> CombatantState:
        combatant = self.combatants.get(character_id)
        if combatant is None:
            raise ValueError(f"Combattente {character_id} non presente nello scontro.")
        return combatant

    def living_combatants(self) -> list[CombatantState]:
        return [combatant for combatant in self.combatants.values() if combatant.alive and not combatant.defeated]

    def add_event(
        self,
        event_type: str,
        description: str,
        actor_id: int | None = None,
        target_id: int | None = None,
        **data: Any,
    ) -> CombatEvent:
        event = CombatEvent(
            round_number=self.round_number,
            actor_id=actor_id,
            target_id=target_id,
            event_type=event_type,
            description=description,
            data=data,
        )
        self.events.append(event)
        return event

    def check_finished(self) -> bool:
        living = self.living_combatants()
        if len(living) > 1:
            return False

        self.phase = "finished"
        if len(living) == 1:
            self.winner_id = living[0].character_id
            self.loser_ids = [
                combatant.character_id
                for combatant in self.combatants.values()
                if combatant.character_id != self.winner_id
            ]
        else:
            self.winner_id = None
            self.loser_ids = list(self.combatants.keys())
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "combat_id": self.combat_id,
            "round_number": self.round_number,
            "phase": self.phase,
            "combatants": {
                str(character_id): combatant.to_dict()
                for character_id, combatant in self.combatants.items()
            },
            "turn_order": list(self.turn_order),
            "events": [event.to_dict() for event in self.events],
            "winner_id": self.winner_id,
            "loser_ids": list(self.loser_ids),
            "metadata": dict(self.metadata),
        }


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Il valore testuale della combat_action non è valido.")
    value = value.strip()
    return value or None


def _bounded_text(value: Any, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError("Il testo della combat_action non è valido.")
    value = value.strip()
    if len(value) > maximum:
        raise ValueError(f"Testo della combat_action troppo lungo (massimo {maximum} caratteri).")
    return value


def combatant_from_character(character: dict[str, Any]) -> CombatantState:
    """Costruisce lo stato iniziale del combattente dai dati persistenti del personaggio."""
    if not isinstance(character, dict):
        raise ValueError("Il personaggio deve essere un dizionario.")

    character_id = character.get("id")
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("Il personaggio non ha un ID valido.")

    identity = character.get("identity", {})
    if not isinstance(identity, dict):
        identity = {}

    name = str(identity.get("name") or "Personaggio").strip()
    surname = str(identity.get("surname") or "").strip()
    if surname:
        name = f"{name} {surname}"

    extra = character.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}

    statistics = extra.get("statistics", {})
    if not isinstance(statistics, dict):
        statistics = {}
    statistics = {
        str(key): int(value)
        for key, value in statistics.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }

    conditions = extra.get("conditions", {})
    if not isinstance(conditions, dict):
        conditions = {}

    max_health = _positive_int(conditions.get("health"), 100)
    max_stamina = _nonnegative_int(conditions.get("stamina"), 100)
    max_mana = _nonnegative_int(conditions.get("mana"), 0)

    abilities = extra.get("abilities", [])
    skills = extra.get("skills", [])
    if not isinstance(abilities, list):
        abilities = []
    if not isinstance(skills, list):
        skills = []

    status = conditions.get("status", "Normale")
    if not isinstance(status, str) or not status.strip():
        status = "Normale"

    return CombatantState(
        character_id=character_id,
        name=name,
        health=max_health,
        max_health=max_health,
        stamina=max_stamina,
        max_stamina=max_stamina,
        mana=max_mana,
        max_mana=max_mana,
        statistics=statistics,
        abilities=[item for item in abilities if isinstance(item, dict)],
        skills=[item for item in skills if isinstance(item, dict)],
        status=status.strip(),
    )


def _positive_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _nonnegative_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, number)
