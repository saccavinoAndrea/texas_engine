"""Metriche accessorie del tavolo: SPR e Minimum Defense Frequency (MDF).

Pura aritmetica, nessun solver. SPR (stack-to-pot ratio) misura quanto è
profondo lo stack effettivo rispetto al piatto, utile per decidere se
committarsi. MDF è la frequenza minima con cui bisognerebbe continuare
contro una puntata data la sua size, per non essere sfruttabili da un
bluff sistematico.
"""

from __future__ import annotations


class InvalidMetricsInputError(ValueError):
    pass


def calculate_spr(effective_stack: float, pot: float) -> float:
    if effective_stack < 0 or pot < 0:
        raise InvalidMetricsInputError("importi negativi non ammessi")
    if pot == 0:
        raise InvalidMetricsInputError("il piatto deve essere maggiore di zero per calcolare l'SPR")
    return effective_stack / pot


def calculate_mdf(pot_before_bet: float, bet_size: float) -> float:
    if pot_before_bet < 0 or bet_size < 0:
        raise InvalidMetricsInputError("importi negativi non ammessi")
    if bet_size == 0:
        raise InvalidMetricsInputError("la size della puntata deve essere maggiore di zero per calcolare l'MDF")
    return pot_before_bet / (pot_before_bet + bet_size)


def calculate_max_implied_bet(effective_stack: float, amount_to_call: float) -> float:
    """Tetto teorico per una stima di implied odds: quanto resta nello stack
    effettivo dopo aver chiamato.

    Non è una previsione di quanto l'avversario pagherà davvero nei giri
    successivi (dipenderebbe dal suo comportamento futuro, terreno di un
    solver): è solo il vincolo fisico imposto dagli stack, utile per tarare
    una stima manuale realistica invece che arbitraria.
    """
    if effective_stack < 0 or amount_to_call < 0:
        raise InvalidMetricsInputError("importi negativi non ammessi")
    return max(0.0, effective_stack - amount_to_call)
