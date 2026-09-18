import itertools
import random

import pytest

from engine.cards import parse_cards, remaining_deck
from engine.equity import InvalidEquityInputError, calculate_equity
from engine.evaluator import compare_hands

MC_ITERATIONS = 60_000
MC_TOLERANCE = 0.02  # 2 punti percentuali: ampio margine rispetto alla std error a 60k iterazioni


def test_preflop_aa_vs_kk_matches_literature():
    hero = parse_cards(["Ah", "As"])
    villain = parse_cards(["Kh", "Ks"])

    result = calculate_equity(hero, [], villain_cards=[villain], iterations=MC_ITERATIONS, rng=random.Random(1))

    assert result.method == "monte_carlo"
    assert result.hero_equity == pytest.approx(0.824, abs=MC_TOLERANCE)


def test_preflop_aa_vs_72o_matches_literature():
    hero = parse_cards(["Ah", "As"])
    villain = parse_cards(["7c", "2d"])

    result = calculate_equity(hero, [], villain_cards=[villain], iterations=MC_ITERATIONS, rng=random.Random(2))

    assert result.method == "monte_carlo"
    assert result.hero_equity == pytest.approx(0.873, abs=MC_TOLERANCE)


def test_flop_flush_draw_plus_overcards_vs_overpair():
    """Scenario da manuale: nut flush draw + due overcard vs coppia sotto, sul flop.

    Con 9 outs a colore + 6 outs di overcard (~15 outs) l'equity supera il 50%,
    spot noto in letteratura come "quasi un coinflip a favore del draw".
    """
    hero = parse_cards(["Ah", "Kh"])
    villain = parse_cards(["Qc", "Qd"])
    board = parse_cards(["Jh", "9h", "2c"])

    result = calculate_equity(hero, board, villain_cards=[villain], iterations=MC_ITERATIONS, rng=random.Random(3))

    assert result.method == "monte_carlo"
    assert result.hero_equity == pytest.approx(0.536, abs=MC_TOLERANCE)


def test_turn_uses_exact_enumeration_and_matches_reference_implementation():
    hero = parse_cards(["Ah", "Kh"])
    villain = parse_cards(["Qc", "Qd"])
    board = parse_cards(["Jh", "9h", "2c", "Td"])

    result = calculate_equity(hero, board, villain_cards=[villain])

    assert result.method == "exact_enumeration"

    # Riferimento indipendente: enumerazione manuale su tutte le river possibili.
    deck = remaining_deck(hero + villain + board)
    hero_wins = hero_ties = 0
    for river in deck:
        winners = compare_hands([hero, villain], board + [river])
        if winners == [0]:
            hero_wins += 1
        elif len(winners) == 2:
            hero_ties += 1
    expected_equity = (hero_wins + hero_ties / 2) / len(deck)

    assert result.hero_equity == pytest.approx(expected_equity, abs=1e-9)
    assert result.trials == len(deck)


def test_river_direct_comparison_hero_wins():
    hero = parse_cards(["Ah", "Kh"])
    villain = parse_cards(["Qc", "Qd"])
    board = parse_cards(["Jh", "9h", "2c", "Td", "3h"])  # hero fa colore

    result = calculate_equity(hero, board, villain_cards=[villain])

    assert result.method == "direct_comparison"
    assert result.hero_equity == 1.0
    assert result.opponents_equity == [0.0]
    assert result.tie_probability == 0.0
    assert result.trials == 1


def test_river_direct_comparison_split_pot():
    # Board a scala che gioca per entrambi: split pot.
    hero = parse_cards(["2c", "3d"])
    villain = parse_cards(["7h", "8s"])
    board = parse_cards(["Ah", "Kd", "Qc", "Jh", "Th"])

    result = calculate_equity(hero, board, villain_cards=[villain])

    assert result.method == "direct_comparison"
    assert result.hero_equity == 0.5
    assert result.opponents_equity == [0.5]
    assert result.tie_probability == 1.0


def test_unknown_opponent_random_hand_preflop():
    hero = parse_cards(["Ah", "As"])

    result = calculate_equity(hero, [], iterations=MC_ITERATIONS, rng=random.Random(4))

    assert result.method == "monte_carlo"
    # AA vs mano random: equity nota in letteratura ~85%
    assert result.hero_equity == pytest.approx(0.852, abs=MC_TOLERANCE)


def test_multiple_known_opponents_flop():
    hero = parse_cards(["Ah", "As"])
    villain1 = parse_cards(["Kh", "Ks"])
    villain2 = parse_cards(["Qh", "Qs"])
    board = parse_cards(["2c", "5d", "9h"])

    result = calculate_equity(
        hero, board, villain_cards=[villain1, villain2], num_opponents=2, iterations=MC_ITERATIONS, rng=random.Random(5)
    )

    assert len(result.opponents_equity) == 2
    total = result.hero_equity + sum(result.opponents_equity)
    assert total == pytest.approx(1.0, abs=1e-9)


def test_rejects_more_than_one_unknown_opponent():
    hero = parse_cards(["Ah", "As"])

    with pytest.raises(InvalidEquityInputError):
        calculate_equity(hero, [], num_opponents=2)


def test_rejects_duplicate_cards():
    hero = parse_cards(["Ah", "As"])
    villain = parse_cards(["Ah", "Kd"])

    with pytest.raises(InvalidEquityInputError):
        calculate_equity(hero, [], villain_cards=[villain])


def test_rejects_invalid_board_length():
    hero = parse_cards(["Ah", "As"])
    board = parse_cards(["2c", "5d"])  # 2 carte non è una fase valida

    with pytest.raises(InvalidEquityInputError):
        calculate_equity(hero, board)
