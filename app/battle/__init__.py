"""Compatibilità per il sistema di combattimento IA.

Il server esistente importa ``app.battle``. Questo package reindirizza
quell'import al nuovo regista che usa il combat engine deterministico.
"""

from app.combat.ai_battle import simulate_battle

__all__ = ["simulate_battle"]
