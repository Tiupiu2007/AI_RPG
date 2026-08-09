"""Deterministic world clock for the AI RPG.

The clock stores absolute in-world time. It does not ask the AI to calculate
elapsed time; game systems advance it explicitly in minutes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class WorldClock:
    """Represents the current absolute time inside a game world."""

    current_time: datetime

    @classmethod
    def create(
        cls,
        *,
        year: int = 1,
        month: int = 1,
        day: int = 1,
        hour: int = 8,
        minute: int = 0,
    ) -> "WorldClock":
        """Create a clock using the game's deterministic calendar."""
        return cls(
            current_time=_build_datetime(year, month, day, hour, minute)
        )

    def advance_minutes(self, minutes: int) -> datetime:
        """Advance world time by a non-negative number of minutes."""
        if not isinstance(minutes, int) or isinstance(minutes, bool):
            raise TypeError("I minuti devono essere un intero.")
        if minutes < 0:
            raise ValueError("Non è possibile riportare indietro il tempo.")

        self.current_time += timedelta(minutes=minutes)
        return self.current_time

    def advance_hours(self, hours: int) -> datetime:
        """Advance world time by a non-negative number of hours."""
        if not isinstance(hours, int) or isinstance(hours, bool):
            raise TypeError("Le ore devono essere un intero.")
        if hours < 0:
            raise ValueError("Non è possibile riportare indietro il tempo.")
        return self.advance_minutes(hours * 60)

    def advance_days(self, days: int) -> datetime:
        """Advance world time by a non-negative number of days."""
        if not isinstance(days, int) or isinstance(days, bool):
            raise TypeError("I giorni devono essere un intero.")
        if days < 0:
            raise ValueError("Non è possibile riportare indietro il tempo.")
        return self.advance_minutes(days * 24 * 60)

    def elapsed_until(self, target: datetime) -> int:
        """Return whole minutes from the current time to a future timestamp."""
        if not isinstance(target, datetime):
            raise TypeError("Il tempo di destinazione deve essere datetime.")
        delta = target - self.current_time
        total_seconds = delta.total_seconds()
        if total_seconds < 0:
            raise ValueError("Il tempo di destinazione è nel passato.")
        return int(total_seconds // 60)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "current_time": self.current_time.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldClock":
        """Rebuild a clock from serialized data."""
        if not isinstance(data, dict):
            raise TypeError("L'orologio del mondo deve essere un dizionario.")

        value = data.get("current_time")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("WorldClock: current_time non valido.")

        try:
            current_time = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError("WorldClock: current_time non valido.") from error

        return cls(current_time=current_time)

    @property
    def year(self) -> int:
        return self.current_time.year

    @property
    def month(self) -> int:
        return self.current_time.month

    @property
    def day(self) -> int:
        return self.current_time.day

    @property
    def hour(self) -> int:
        return self.current_time.hour

    @property
    def minute(self) -> int:
        return self.current_time.minute

    def formatted(self) -> str:
        """Return a compact human-readable timestamp."""
        return self.current_time.strftime("Anno %Y-%m-%d %H:%M")


def _build_datetime(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
) -> datetime:
    values = (year, month, day, hour, minute)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise TypeError("I valori del calendario devono essere interi.")

    try:
        return datetime(year, month, day, hour, minute)
    except ValueError as error:
        raise ValueError(f"Data o ora non valida: {error}") from error
