"""Wrapper sottile su treys per valutare la forza di una mano (5-7 carte)."""

from __future__ import annotations

from treys import Card as TreysCard
from treys import Evaluator as TreysEvaluator

from engine.cards import Card

_evaluator = TreysEvaluator()


def _to_treys(card: Card) -> int:
    return TreysCard.new(str(card))


def hand_rank(hole_cards: list[Card], board: list[Card]) -> int:
    """Ritorna il rank treys della mano migliore a 5 carte (più basso = più forte)."""
    return _evaluator.evaluate(
        [_to_treys(c) for c in board],
        [_to_treys(c) for c in hole_cards],
    )


def compare_hands(hole_cards_list: list[list[Card]], board: list[Card]) -> list[int]:
    """Indici (0-based) delle mani vincenti; più di un indice in caso di split pot."""
    ranks = [hand_rank(hole_cards, board) for hole_cards in hole_cards_list]
    best = min(ranks)
    return [i for i, r in enumerate(ranks) if r == best]
