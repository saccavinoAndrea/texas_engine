import itertools
import random

import pytest

from collections import Counter

from engine.cards import Card, full_deck, parse_cards, remaining_deck
from engine.equity import InvalidEquityInputError, _deal_trial, calculate_equity
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


def test_two_unknown_opponents_preflop_matches_literature():
    hero = parse_cards(["Ah", "As"])

    result = calculate_equity(hero, [], num_opponents=2, iterations=MC_ITERATIONS, rng=random.Random(10))

    assert result.method == "monte_carlo"
    assert len(result.opponents_equity) == 2
    # AA vs 2 mani random: equity nota in letteratura ~73.4%
    assert result.hero_equity == pytest.approx(0.734, abs=MC_TOLERANCE)
    assert result.hero_equity + sum(result.opponents_equity) == pytest.approx(1.0, abs=1e-9)


def test_three_unknown_opponents_preflop_matches_literature():
    hero = parse_cards(["Ah", "As"])

    result = calculate_equity(hero, [], num_opponents=3, iterations=MC_ITERATIONS, rng=random.Random(11))

    assert result.method == "monte_carlo"
    assert len(result.opponents_equity) == 3
    # AA vs 3 mani random: equity nota in letteratura ~63.8%
    assert result.hero_equity == pytest.approx(0.638, abs=MC_TOLERANCE)
    assert result.hero_equity + sum(result.opponents_equity) == pytest.approx(1.0, abs=1e-9)


def test_two_unknown_opponents_on_turn_falls_back_to_monte_carlo():
    """Con 2+ avversari ignoti l'enumerazione esatta esploderebbe combinatoriamente:
    anche su turn/river si passa a Monte Carlo."""
    hero = parse_cards(["Ah", "As"])
    board = parse_cards(["2c", "5d", "9h", "Jd"])

    result = calculate_equity(hero, board, num_opponents=2, iterations=5000, rng=random.Random(12))

    assert result.method == "monte_carlo"
    assert result.trials == 5000


def test_mixed_known_and_unknown_opponents():
    """1 avversario noto + 1 ignoto: deve comunque funzionare (Monte Carlo)."""
    hero = parse_cards(["Ah", "As"])
    known_villain = parse_cards(["Kh", "Ks"])
    board = parse_cards(["2c", "5d", "9h"])

    result = calculate_equity(
        hero, board, villain_cards=[known_villain], num_opponents=3, iterations=MC_ITERATIONS, rng=random.Random(13)
    )

    assert result.method == "monte_carlo"
    assert len(result.opponents_equity) == 3
    assert result.hero_equity + sum(result.opponents_equity) == pytest.approx(1.0, abs=1e-9)


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


def test_villain_range_matches_reference_value():
    hero = parse_cards(["Ah", "As"])

    result = calculate_equity(
        hero, [], villain_ranges=[["KK", "QQ", "AKs"]], iterations=MC_ITERATIONS, rng=random.Random(20)
    )

    assert result.method == "monte_carlo"
    assert result.hero_equity == pytest.approx(0.826, abs=MC_TOLERANCE)


def test_villain_range_excludes_hero_blockers():
    # AKs ha 4 combo; con Ah/As già in mano all'eroe, ne restano solo 2 (una per seme mancante)
    hero = parse_cards(["Ah", "As"])

    result = calculate_equity(hero, [], villain_ranges=[["AKs"]], iterations=20000, rng=random.Random(23))

    assert result.method == "monte_carlo"
    assert result.trials == 20000


def test_known_villain_and_ranged_villain_together():
    hero = parse_cards(["Ah", "As"])
    known_villain = parse_cards(["2c", "2d"])

    result = calculate_equity(
        hero,
        [],
        villain_cards=[known_villain],
        villain_ranges=[["KK", "AKs"]],
        num_opponents=2,
        iterations=MC_ITERATIONS,
        rng=random.Random(21),
    )

    assert result.method == "monte_carlo"
    assert len(result.opponents_equity) == 2
    assert result.hero_equity + sum(result.opponents_equity) == pytest.approx(1.0, abs=1e-9)


def test_range_on_turn_forces_monte_carlo():
    """Un range forza sempre Monte Carlo, anche su turn/river dove normalmente
    si userebbe l'enumerazione esatta: evita l'esplosione combinatoria."""
    hero = parse_cards(["Ah", "As"])
    board = parse_cards(["2c", "5d", "9h", "Jd"])

    result = calculate_equity(hero, board, villain_ranges=[["KK", "QQ"]], iterations=5000, rng=random.Random(22))

    assert result.method == "monte_carlo"
    assert result.trials == 5000


def test_rejects_empty_range():
    hero = parse_cards(["Ah", "As"])

    with pytest.raises(InvalidEquityInputError):
        calculate_equity(hero, [], villain_ranges=[[]])


def test_rejects_fully_blocked_range():
    hero = parse_cards(["Ah", "As"])
    board = parse_cards(["Kc", "Kd", "Kh", "Ks"])  # tutti i re già sul board

    with pytest.raises(InvalidEquityInputError):
        calculate_equity(hero, board, villain_ranges=[["KK"]])


def test_rejects_too_many_known_and_ranged_opponents():
    hero = parse_cards(["Ah", "As"])
    known_villain = parse_cards(["2c", "2d"])

    with pytest.raises(InvalidEquityInputError):
        calculate_equity(hero, [], villain_cards=[known_villain], villain_ranges=[["KK"]], num_opponents=1)


def test_deal_trial_two_overlapping_ranges_gives_uniform_feasible_joint_distribution():
    """Controesempio: un filtraggio sequenziale (pesca il primo pool, poi
    filtra il secondo su quanto resta) produce un bias quando i due pool si
    bloccano a vicenda in modo asimmetrico. Qui pool_a = {A, B}, pool_b = {C, D}
    con A che confligge solo con C (condividono 7h), mentre B non confligge con
    nessuno dei due. Le tre coppie congiuntamente compatibili sono (A,D), (B,C),
    (B,D): con un dealing corretto devono uscire ciascuna ~1/3 delle volte.
    Un filtraggio sequenziale darebbe invece (A,D)=1/2, (B,C)=1/4, (B,D)=1/4.
    """
    A = (Card("7", "h"), Card("6", "h"))
    B = (Card("7", "s"), Card("6", "s"))
    C = (Card("7", "h"), Card("5", "h"))  # confligge con A (condivide 7h)
    D = (Card("9", "c"), Card("8", "d"))  # non confligge né con A né con B

    # unknown_board_count e unknown_random_count sono 0 in questo test: il
    # mazzo residuo non viene mai campionato, serve solo come parametro.
    deck = full_deck()
    rng = random.Random(42)

    trials = 30_000
    outcomes: Counter[tuple[str, str]] = Counter()
    for _ in range(trials):
        _, hands = _deal_trial(rng, deck, unknown_board_count=0, unknown_random_count=0, range_pools=[[A, B], [C, D]])
        first = "A" if hands[0] == list(A) else "B"
        second = "C" if hands[1] == list(C) else "D"
        outcomes[(first, second)] += 1

    assert outcomes[("A", "C")] == 0  # combinazione infeasible: mai dovrebbe uscire

    for pair in [("A", "D"), ("B", "C"), ("B", "D")]:
        frequency = outcomes[pair] / trials
        assert frequency == pytest.approx(1 / 3, abs=0.02)
