from dataclasses import dataclass, field
from typing import Any


@dataclass
class Money:
    """Currencies owned by a character.

    Values are kept per currency instead of assuming a single universal coin.
    The engine can later define exchange rates without changing the character model.
    """

    currencies: dict[str, float] = field(default_factory=dict)

    def get(self, currency: str) -> float:
        return float(self.currencies.get(currency, 0.0))

    def add(self, currency: str, amount: float) -> None:
        if amount < 0:
            raise ValueError("Non puoi aggiungere una quantita negativa di denaro.")
        self.currencies[currency] = self.get(currency) + amount

    def remove(self, currency: str, amount: float) -> None:
        if amount < 0:
            raise ValueError("Non puoi rimuovere una quantita negativa di denaro.")
        if self.get(currency) < amount:
            raise ValueError("Denaro insufficiente.")
        self.currencies[currency] = self.get(currency) - amount

    def to_dict(self) -> dict[str, Any]:
        return dict(self.currencies)
