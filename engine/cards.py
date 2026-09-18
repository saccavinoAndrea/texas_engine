"""Rappresentazione delle carte e del mazzo, indipendente da qualsiasi libreria di valutazione."""

from __future__ import annotations

import random
from dataclasses import dataclass

RANKS = "23456789TJQKA"
SUITS = "cdhs"


class InvalidCardError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Card:
    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANKS:
            raise InvalidCardError(f"rank non valido: {self.rank!r}")
        if self.suit not in SUITS:
            raise InvalidCardError(f"seme non valido: {self.suit!r}")

    @classmethod
    def parse(cls, code: str) -> "Card":
        if not isinstance(code, str) or len(code) != 2:
            raise InvalidCardError(f"formato carta non valido: {code!r} (atteso es. 'Ah', 'Td')")
        rank, suit = code[0].upper(), code[1].lower()
        return cls(rank, suit)

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    def __repr__(self) -> str:
        return f"Card('{self}')"


def parse_cards(codes: list[str]) -> list[Card]:
    return [Card.parse(code) for code in codes]


def full_deck() -> list[Card]:
    return [Card(rank, suit) for suit in SUITS for rank in RANKS]


def remaining_deck(known_cards: list[Card]) -> list[Card]:
    """Mazzo residuo escludendo le carte già note (hero, board, eventuali avversari)."""
    known = set(known_cards)
    if len(known) != len(known_cards):
        raise InvalidCardError("carte duplicate tra quelle note")
    return [card for card in full_deck() if card not in known]


def draw_random(deck: list[Card], count: int, rng: random.Random | None = None) -> list[Card]:
    rng = rng or random
    return rng.sample(deck, count)
