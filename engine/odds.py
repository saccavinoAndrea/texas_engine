"""Pot odds: funzione pura e deterministica, nessuna dipendenza da equity/evaluator."""

from __future__ import annotations


class InvalidPotOddsInputError(ValueError):
    pass


def pot_odds(
    amount_to_call: float,
    pot_before_call: float,
    implied_future_bet: float = 0.0,
) -> float:
    """Equity minima richiesta (0..1) per un call profittevole.

    required_equity = amount_to_call / (pot_before_call + amount_to_call + implied_future_bet)

    Con implied_future_bet = 0 sono le pot odds pure: quanto ti serve guardando
    solo i soldi già sul tavolo. Passando la stima di quanto incasseresti in più
    nei giri successivi si ottiene invece la soglia di pareggio effettiva, la
    stessa a cui risponde l'EV: senza di essa i due numeri si contraddicono a
    schermo, perché l'EV tiene conto delle implied odds e le pot odds no.
    """
    if amount_to_call < 0 or pot_before_call < 0 or implied_future_bet < 0:
        raise InvalidPotOddsInputError("importi negativi non ammessi")
    if amount_to_call == 0:
        return 0.0
    return amount_to_call / (pot_before_call + amount_to_call + implied_future_bet)
