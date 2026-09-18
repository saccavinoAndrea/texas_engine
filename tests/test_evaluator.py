"""Test diretti sull'evaluator: è il componente che decide chi vince ogni mano,
quindi non basta la copertura indiretta che arriva dai test sull'equity."""

import pytest

from engine.cards import parse_cards
from engine.evaluator import compare_hands, hand_rank

# Una mano per categoria, dalla più forte alla più debole. I rank treys sono
# assoluti (1 = scala reale), quindi sono confrontabili anche fra board diversi.
HANDS_STRONGEST_TO_WEAKEST = [
    ("scala reale", ["Ah", "Kh"], ["Qh", "Jh", "Th", "2c", "3d"]),
    ("poker", ["9c", "9d"], ["9h", "9s", "2c", "3d", "4h"]),
    ("full", ["Kc", "Kd"], ["Kh", "2c", "2d", "7s", "9h"]),
    ("colore", ["Ah", "2h"], ["Kh", "9h", "4h", "3c", "7d"]),
    ("scala", ["Ts", "9d"], ["8c", "7h", "6s", "2d", "Kc"]),
    ("tris", ["Qc", "Qd"], ["Qh", "2c", "7d", "9s", "4h"]),
    ("doppia coppia", ["Ac", "Kd"], ["Ah", "Kc", "2d", "7s", "9h"]),
    ("coppia", ["Ac", "Qd"], ["Ah", "5c", "8d", "Ts", "2h"]),
    ("carta alta", ["Ac", "Qd"], ["9h", "5c", "8d", "2s", "3h"]),
]


def test_hand_rank_orders_categories_correctly():
    ranks = [
        (label, hand_rank(parse_cards(hole), parse_cards(board)))
        for label, hole, board in HANDS_STRONGEST_TO_WEAKEST
    ]

    for (stronger_label, stronger), (weaker_label, weaker) in zip(ranks, ranks[1:]):
        assert stronger < weaker, f"{stronger_label} dovrebbe battere {weaker_label}"


def test_hand_rank_royal_flush_is_the_best_possible():
    assert hand_rank(parse_cards(["Ah", "Kh"]), parse_cards(["Qh", "Jh", "Th", "2c", "3d"])) == 1


def test_hand_rank_uses_the_best_five_of_seven():
    """Le due carte coperte vanno ignorate quando il board da solo fa di meglio."""
    board = parse_cards(["Ah", "Kh", "Qh", "Jh", "Th"])  # scala reale che gioca per tutti

    assert hand_rank(parse_cards(["2c", "7d"]), board) == hand_rank(parse_cards(["3s", "8d"]), board)


def test_compare_hands_returns_the_single_winner():
    board = parse_cards(["Ah", "Kd", "7c", "2s", "9h"])
    hero = parse_cards(["Ac", "Qd"])  # coppia di assi
    villain = parse_cards(["Kc", "Jd"])  # coppia di re

    assert compare_hands([hero, villain], board) == [0]
    assert compare_hands([villain, hero], board) == [1]  # l'ordine non cambia il verdetto


def test_compare_hands_returns_every_player_on_a_split():
    board = parse_cards(["Ah", "Kd", "Qc", "Js", "Th"])  # scala che gioca per tutti
    players = [parse_cards(["2c", "3d"]), parse_cards(["4h", "5s"]), parse_cards(["6c", "7d"])]

    assert compare_hands(players, board) == [0, 1, 2]


def test_compare_hands_resolves_by_kicker():
    board = parse_cards(["Ah", "7d", "2c", "9s", "4h"])
    better_kicker = parse_cards(["Ac", "Kd"])
    worse_kicker = parse_cards(["As", "Qd"])

    assert compare_hands([better_kicker, worse_kicker], board) == [0]


def test_hand_rank_is_consistent_regardless_of_card_order():
    board = parse_cards(["Ah", "Kd", "7c", "2s", "9h"])
    hole = parse_cards(["Ac", "Qd"])

    assert hand_rank(hole, board) == hand_rank(hole[::-1], board[::-1])
