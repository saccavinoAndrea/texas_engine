"""Calcolo dell'EV (expected value) di una chiamata: funzione pura, nessun solver.

EV(call) = equity * (piatto_prima_del_call + importo_da_chiamare) - importo_da_chiamare

Si assume la mano già decisa a showdown (nessuna proiezione su strade future,
nessuna fold equity): coerente con lo scope attuale (equity + pot odds sulla mano corrente).
"""

from __future__ import annotations


class InvalidEvInputError(ValueError):
    pass


def calculate_call_ev(hero_equity: float, amount_to_call: float, pot_before_call: float) -> float:
    if not 0.0 <= hero_equity <= 1.0:
        raise InvalidEvInputError("hero_equity deve essere compreso tra 0 e 1")
    if amount_to_call < 0 or pot_before_call < 0:
        raise InvalidEvInputError("importi negativi non ammessi")

    pot_after_call = pot_before_call + amount_to_call
    return hero_equity * pot_after_call - amount_to_call
