"""Calcolo dell'EV (expected value) di una chiamata: funzione pura, nessun solver.

EV(call) = equity * (piatto_prima_del_call + importo_da_chiamare) - importo_da_chiamare

Si assume la mano già decisa a showdown (nessuna proiezione su strade future,
nessuna fold equity): coerente con lo scope attuale (equity + pot odds sulla mano corrente).
"""

from __future__ import annotations


class InvalidEvInputError(ValueError):
    pass


def calculate_call_ev(
    hero_equity: float,
    amount_to_call: float,
    pot_before_call: float,
    implied_future_bet: float = 0.0,
) -> float:
    """implied_future_bet: puntate future stimate dall'utente che l'eroe
    incasserebbe in più solo se vince a showdown (implied odds). È una stima
    manuale come la fold_probability dello shove, non calcolata dal motore.
    """
    if not 0.0 <= hero_equity <= 1.0:
        raise InvalidEvInputError("hero_equity deve essere compreso tra 0 e 1")
    if amount_to_call < 0 or pot_before_call < 0 or implied_future_bet < 0:
        raise InvalidEvInputError("importi negativi non ammessi")

    pot_after_call = pot_before_call + amount_to_call + implied_future_bet
    return hero_equity * pot_after_call - amount_to_call


def calculate_shove_ev(
    hero_equity_if_called: float,
    fold_probability: float,
    pot_before_shove: float,
    shove_amount: float,
    villain_already_in: float = 0.0,
) -> float:
    """EV di un all-in (shove) con fold equity.

    fold_probability è una stima fornita dall'utente (una lettura sull'avversario),
    non calcolata dal motore: resta pura aritmetica, nessun solver.

    EV = P(fold) * piatto_attuale
       + P(call) * [equity_se_chiamato * piatto_finale - importo_shove]

    Se l'avversario folda, l'eroe vince il piatto esistente (il proprio shove torna
    a sé, nessuno lo ha eguagliato). Se chiama, deve aggiungere solo la differenza
    fra lo shove e quanto ha già messo nel piatto in questo giro
    (villain_already_in, cioè l'importo che l'eroe avrebbe altrimenti dovuto
    chiamare): quella parte è già dentro pot_before_shove, e chiedergli di nuovo
    l'intero shove gonfierebbe il piatto finale. Il piatto a showdown è quindi
    piatto_attuale + 2*shove - quanto_gia_messo, che con un piatto non ancora
    puntato (villain_already_in = 0) torna al più familiare piatto + 2*shove.
    """
    if not 0.0 <= hero_equity_if_called <= 1.0:
        raise InvalidEvInputError("hero_equity_if_called deve essere compreso tra 0 e 1")
    if not 0.0 <= fold_probability <= 1.0:
        raise InvalidEvInputError("fold_probability deve essere compresa tra 0 e 1")
    if pot_before_shove < 0 or shove_amount < 0 or villain_already_in < 0:
        raise InvalidEvInputError("importi negativi non ammessi")
    if villain_already_in > pot_before_shove:
        raise InvalidEvInputError("la puntata avversaria non può superare il piatto, che la comprende già")
    if villain_already_in >= shove_amount:
        raise InvalidEvInputError(
            "lo shove deve superare la puntata avversaria: altrimenti l'avversario non ha nulla da foldare"
        )

    call_probability = 1.0 - fold_probability
    ev_if_fold = pot_before_shove
    pot_if_called = pot_before_shove + 2 * shove_amount - villain_already_in
    ev_if_called = hero_equity_if_called * pot_if_called - shove_amount

    return fold_probability * ev_if_fold + call_probability * ev_if_called
