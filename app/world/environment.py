"""Deterministic environmental conditions derived from world time and geography."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math


SEASONS = ("inverno", "primavera", "estate", "autunno")
DAY_PHASES = ("notte", "alba", "giorno", "tramonto")


@dataclass(frozen=True)
class EnvironmentConditions:
    """Conditions at a specific point in the world at a specific time."""

    season: str
    day_phase: str
    temperature_c: float
    precipitation: float
    wind: float
    humidity: float
    snow: float
    fog: float
    is_storm: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "season": self.season,
            "day_phase": self.day_phase,
            "temperature_c": self.temperature_c,
            "precipitation": self.precipitation,
            "wind": self.wind,
            "humidity": self.humidity,
            "snow": self.snow,
            "fog": self.fog,
            "is_storm": self.is_storm,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnvironmentConditions":
        return cls(
            season=str(data["season"]),
            day_phase=str(data["day_phase"]),
            temperature_c=float(data["temperature_c"]),
            precipitation=float(data["precipitation"]),
            wind=float(data["wind"]),
            humidity=float(data["humidity"]),
            snow=float(data["snow"]),
            fog=float(data["fog"]),
            is_storm=bool(data["is_storm"]),
        )


@dataclass
class EnvironmentEngine:
    """Calculates repeatable conditions without asking the AI to invent them."""

    seed: int = 0

    def conditions_at(
        self,
        *,
        year: int,
        day_of_year: int,
        hour: int,
        minute: int,
        x: float = 0.0,
        y: float = 0.0,
        latitude: float = 0.0,
        altitude: float = 0.0,
        biome: str | None = None,
    ) -> EnvironmentConditions:
        day_of_year = max(1, min(365, int(day_of_year)))
        hour = max(0, min(23, int(hour)))
        minute = max(0, min(59, int(minute)))

        season_index = min(3, (day_of_year - 1) // 91)
        season = SEASONS[season_index]
        day_phase = self._day_phase(hour, minute)

        latitude_factor = max(-1.0, min(1.0, latitude / 90.0))
        seasonal_wave = math.cos((day_of_year - 172) / 365.0 * 2.0 * math.pi)
        daily_wave = math.cos(((hour * 60 + minute) - 14 * 60) / (24 * 60) * 2.0 * math.pi)
        spatial = self._noise(x * 0.008, y * 0.008, year)

        temperature = 18.0 + 16.0 * (1.0 - abs(latitude_factor)) + 10.0 * seasonal_wave * (1.0 - 0.55 * abs(latitude_factor))
        temperature += 4.0 * daily_wave - altitude * 0.006 + spatial * 3.0

        biome_name = (biome or "").casefold()
        if "desert" in biome_name:
            temperature += 7.0
        elif "tundra" in biome_name or "glacier" in biome_name or "ice" in biome_name:
            temperature -= 14.0
        elif "mountain" in biome_name:
            temperature -= 4.0

        humidity = self._clamp(0.50 + self._noise(x * 0.014 + 100, y * 0.014 + 100, year + 17) * 0.35)
        if "desert" in biome_name:
            humidity *= 0.45
        elif "forest" in biome_name:
            humidity = min(1.0, humidity + 0.20)

        precipitation = self._clamp(humidity * 0.72 + self._noise(x * 0.025, y * 0.025, year + day_of_year) * 0.22 - 0.18)
        if "desert" in biome_name:
            precipitation *= 0.30

        wind = self._clamp(0.28 + abs(self._noise(x * 0.02 + 300, y * 0.02 + 300, year + day_of_year)) * 0.58)
        snow = self._clamp(precipitation * max(0.0, (2.5 - temperature) / 8.0))
        fog = self._clamp(humidity * 0.55 + precipitation * 0.25 - wind * 0.30)
        is_storm = precipitation > 0.78 and wind > 0.72

        return EnvironmentConditions(
            season=season,
            day_phase=day_phase,
            temperature_c=round(temperature, 2),
            precipitation=round(precipitation, 3),
            wind=round(wind, 3),
            humidity=round(humidity, 3),
            snow=round(snow, 3),
            fog=round(fog, 3),
            is_storm=is_storm,
        )

    @staticmethod
    def _day_phase(hour: int, minute: int) -> str:
        total = hour * 60 + minute
        if total < 5 * 60 + 30 or total >= 21 * 60:
            return "notte"
        if total < 7 * 60:
            return "alba"
        if total < 19 * 60 + 30:
            return "giorno"
        return "tramonto"

    def _noise(self, x: float, y: float, t: int) -> float:
        value = math.sin(x * 12.9898 + y * 78.233 + t * 37.719 + self.seed * 11.173) * 43758.5453
        return (value - math.floor(value)) * 2.0 - 1.0

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))


def day_of_year(month: int, day: int) -> int:
    """Return a deterministic 1..365 day index for the current calendar."""
    month_lengths = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if month < 1 or month > 12 or day < 1 or day > month_lengths[month - 1]:
        raise ValueError("Data non valida.")
    return sum(month_lengths[: month - 1]) + day
