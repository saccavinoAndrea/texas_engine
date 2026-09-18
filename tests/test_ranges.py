import pytest

from engine.cards import parse_cards
from engine.ranges import InvalidRangeError, count_range_combos, expand_range, hand_class_combos


def test_pair_has_six_combos():
    combos = hand_class_combos("77")
    assert len(combos) == 6
    for c1, c2 in combos:
        assert c1.rank == "7" and c2.rank == "7"
        assert c1.suit != c2.suit


def test_suited_has_four_combos():
    combos = hand_class_combos("AKs")
    assert len(combos) == 4
    for c1, c2 in combos:
        assert {c1.rank, c2.rank} == {"A", "K"}
        assert c1.suit == c2.suit


def test_offsuit_has_twelve_combos():
    combos = hand_class_combos("AKo")
    assert len(combos) == 12
    for c1, c2 in combos:
        assert {c1.rank, c2.rank} == {"A", "K"}
        assert c1.suit != c2.suit


def test_rejects_pair_with_suffix():
    with pytest.raises(InvalidRangeError):
        hand_class_combos("77s")


def test_rejects_non_pair_without_suffix():
    with pytest.raises(InvalidRangeError):
        hand_class_combos("AK")


def test_rejects_invalid_rank():
    with pytest.raises(InvalidRangeError):
        hand_class_combos("A1s")


def test_rejects_invalid_suffix():
    with pytest.raises(InvalidRangeError):
        hand_class_combos("AKx")


def test_expand_range_merges_multiple_classes_without_duplicates():
    combos = expand_range(["AA", "AKs"], excluded_cards=[])
    assert len(combos) == 6 + 4


def test_expand_range_excludes_known_cards():
    excluded = parse_cards(["Ah", "Ks"])
    combos = expand_range(["AKs"], excluded_cards=excluded)
    # AKs ha 4 combo (una per seme); quella con Ah e quella con Ks sono bloccate
    # dalle carte escluse -> restano al massimo 2 combo utilizzabili.
    assert len(combos) == 2
    for c1, c2 in combos:
        assert c1 not in excluded and c2 not in excluded


def test_expand_range_rejects_empty_range():
    with pytest.raises(InvalidRangeError):
        expand_range([], excluded_cards=[])


def test_expand_range_rejects_fully_blocked_range():
    excluded = parse_cards(["7c", "7d", "7h", "7s"])
    with pytest.raises(InvalidRangeError):
        expand_range(["77"], excluded_cards=excluded)


def test_count_range_combos_matches_expand_range_length():
    assert count_range_combos(["AA", "AKs"], excluded_cards=[]) == 6 + 4


def test_count_range_combos_accounts_for_blockers():
    excluded = parse_cards(["Ah", "Ks"])
    assert count_range_combos(["AKs"], excluded_cards=excluded) == 2


def test_count_range_combos_returns_zero_for_empty_range():
    assert count_range_combos([], excluded_cards=[]) == 0


def test_count_range_combos_returns_zero_when_fully_blocked_instead_of_raising():
    excluded = parse_cards(["7c", "7d", "7h", "7s"])
    assert count_range_combos(["77"], excluded_cards=excluded) == 0
