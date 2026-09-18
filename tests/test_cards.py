import pytest

from engine.cards import Card, InvalidCardError, full_deck, parse_cards, remaining_deck


def test_parse_card_roundtrip():
    card = Card.parse("Ah")
    assert card.rank == "A"
    assert card.suit == "h"
    assert str(card) == "Ah"


def test_parse_card_case_insensitive():
    assert Card.parse("ah") == Card.parse("Ah")


def test_parse_invalid_rank():
    with pytest.raises(InvalidCardError):
        Card.parse("1h")


def test_parse_invalid_suit():
    with pytest.raises(InvalidCardError):
        Card.parse("Ax")


def test_parse_invalid_length():
    with pytest.raises(InvalidCardError):
        Card.parse("Ahh")


def test_full_deck_has_52_unique_cards():
    deck = full_deck()
    assert len(deck) == 52
    assert len(set(deck)) == 52


def test_remaining_deck_excludes_known_cards():
    known = parse_cards(["Ah", "Kd"])
    deck = remaining_deck(known)
    assert len(deck) == 50
    assert Card.parse("Ah") not in deck
    assert Card.parse("Kd") not in deck


def test_remaining_deck_rejects_duplicates():
    known = parse_cards(["Ah", "Ah"])
    with pytest.raises(InvalidCardError):
        remaining_deck(known)
