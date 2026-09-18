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


def calculate_mdf(pot_before_call: float, amount_to_call: float) -> float:
    """Minimum Defense Frequency contro la puntata che si sta fronteggiando.

    Per definizione, contro una puntata b in un piatto P bisogna continuare almeno
    P / (P + b) delle volte perché un bluff sistematico non diventi automaticamente
    profittevole. Il punto delicato è quale piatto: P è quello PRIMA della puntata
    avversaria, mentre qui il piatto arriva come lo inserisce l'utente, cioè già
    comprensivo della puntata da chiamare (la stessa convenzione usata da pot odds
    ed EV). Tornando indietro al piatto precedente la formula si semplifica in
    (piatto - puntata) / piatto: usare direttamente il piatto comprensivo
    sovrastimerebbe l'MDF, per esempio dando 66,7% invece di 50% su una puntata
    pari al piatto.
    """
    if pot_before_call < 0 or amount_to_call < 0:
        raise InvalidMetricsInputError("importi negativi non ammessi")
    if amount_to_call == 0:
        raise InvalidMetricsInputError("serve una puntata da fronteggiare per calcolare l'MDF")
    if amount_to_call > pot_before_call:
        raise InvalidMetricsInputError("l'importo da chiamare non può superare il piatto, che lo comprende già")
    return (pot_before_call - amount_to_call) / pot_before_call


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
