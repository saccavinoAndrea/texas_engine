"""Pot odds: funzione pura e deterministica, nessuna dipendenza da equity/evaluator."""

from __future__ import annotations


class InvalidPotOddsInputError(ValueError):
    pass


def pot_odds(amount_to_call: float, pot_before_call: float) -> float:
    """Equity minima richiesta (0..1) per un call profittevole.

    required_equity = amount_to_call / (pot_before_call + amount_to_call)
    """
    if amount_to_call < 0 or pot_before_call < 0:
        raise InvalidPotOddsInputError("importi negativi non ammessi")
    if amount_to_call == 0:
        return 0.0
    return amount_to_call / (pot_before_call + amount_to_call)
