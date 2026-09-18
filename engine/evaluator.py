"""Wrapper sottile su treys per valutare la forza di una mano (5-7 carte)."""

from __future__ import annotations

from treys import Card as TreysCard
from treys import Evaluator as TreysEvaluator

from engine.cards import Card, full_deck

_evaluator = TreysEvaluator()

# La conversione verso treys passa per una stringa: ripeterla ad ogni mano di ogni
# trial pesa, visto che equity ne valuta decine di migliaia. Le carte possibili sono
# solo le 52 del mazzo e ogni Card è validata alla costruzione, quindi la tabella si
# costruisce una volta sola all'import ed è completa per definizione.
_TREYS_BY_CARD = {card: TreysCard.new(str(card)) for card in full_deck()}


def _rank(treys_board: list[int], hole_cards: list[Card]) -> int:
    return _evaluator.evaluate(treys_board, [_TREYS_BY_CARD[c] for c in hole_cards])


def hand_rank(hole_cards: list[Card], board: list[Card]) -> int:
    """Ritorna il rank treys della mano migliore a 5 carte (più basso = più forte)."""
    return _rank([_TREYS_BY_CARD[c] for c in board], hole_cards)


def compare_hands(hole_cards_list: list[list[Card]], board: list[Card]) -> list[int]:
    """Indici (0-based) delle mani vincenti; più di un indice in caso di split pot.

    Il board si converte una volta sola e si riusa per tutti i giocatori: è lo
    stesso per definizione, e questa è la funzione più calda dell'applicazione
    (un Monte Carlo la chiama ventimila volte, una per ogni giocatore in mano).
    Rifarne la conversione a ogni giocatore costava circa il 15% del tempo totale.
    """
    treys_board = [_TREYS_BY_CARD[c] for c in board]
    ranks = [_rank(treys_board, hole_cards) for hole_cards in hole_cards_list]
    best = min(ranks)
    return [i for i, r in enumerate(ranks) if r == best]
