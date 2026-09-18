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


def calculate_shove_ev(
    hero_equity_if_called: float,
    fold_probability: float,
    pot_before_shove: float,
    shove_amount: float,
) -> float:
    """EV di un all-in (shove) con fold equity.

    fold_probability è una stima fornita dall'utente (una lettura sull'avversario),
    non calcolata dal motore: resta pura aritmetica, nessun solver.

    EV = P(fold) * piatto_attuale
       + P(call) * [equity_se_chiamato * (piatto_attuale + 2*importo_shove) - importo_shove]

    Se l'avversario folda, l'eroe vince il piatto esistente (il proprio shove torna a sé,
    nessuno lo ha eguagliato). Se chiama, si gioca a showdown per piatto_attuale + 2*importo_shove.
    """
    if not 0.0 <= hero_equity_if_called <= 1.0:
        raise InvalidEvInputError("hero_equity_if_called deve essere compreso tra 0 e 1")
    if not 0.0 <= fold_probability <= 1.0:
        raise InvalidEvInputError("fold_probability deve essere compresa tra 0 e 1")
    if pot_before_shove < 0 or shove_amount < 0:
        raise InvalidEvInputError("importi negativi non ammessi")

    call_probability = 1.0 - fold_probability
    ev_if_fold = pot_before_shove
    pot_if_called = pot_before_shove + 2 * shove_amount
    ev_if_called = hero_equity_if_called * pot_if_called - shove_amount

    return fold_probability * ev_if_fold + call_probability * ev_if_called
