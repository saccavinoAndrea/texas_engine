"""Calcolo dell'equity: Monte Carlo su preflop/flop, enumerazione esatta su turn/river."""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from engine.cards import Card, InvalidCardError, remaining_deck
from engine.evaluator import compare_hands

DEFAULT_ITERATIONS = 20_000


class InvalidEquityInputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EquityResult:
    hero_equity: float
    opponents_equity: list[float]
    tie_probability: float
    method: str
    trials: int


def _validate_input(
    hero_cards: list[Card],
    board: list[Card],
    known_villain_hands: list[list[Card]],
    num_opponents: int,
) -> None:
    if len(hero_cards) != 2:
        raise InvalidEquityInputError("hero_cards deve contenere esattamente 2 carte")
    if len(board) not in (0, 3, 4, 5):
        raise InvalidEquityInputError("board deve avere 0 (preflop), 3 (flop), 4 (turn) o 5 (river) carte")
    if num_opponents < 1:
        raise InvalidEquityInputError("num_opponents deve essere >= 1")
    if len(known_villain_hands) > num_opponents:
        raise InvalidEquityInputError("villain_cards non può contenere più mani di num_opponents")
    for hand in known_villain_hands:
        if len(hand) != 2:
            raise InvalidEquityInputError("ogni mano avversaria nota deve avere esattamente 2 carte")

    unknown_opponents = num_opponents - len(known_villain_hands)
    if unknown_opponents > 1:
        raise InvalidEquityInputError(
            "MVP: al massimo un avversario con mano ignota/random è supportato "
            "(multi-way con più range ignoti è fuori scope per questa fase)"
        )

    all_known = hero_cards + board + [c for hand in known_villain_hands for c in hand]
    if len(set(all_known)) != len(all_known):
        raise InvalidEquityInputError("carte duplicate tra hero/board/villain")


def _players_after_deal(
    hero_cards: list[Card],
    known_villain_hands: list[list[Card]],
    unknown_villain: bool,
    draw: list[Card],
    unknown_board_count: int,
) -> list[list[Card]]:
    players = [hero_cards, *known_villain_hands]
    if unknown_villain:
        players.append(draw[unknown_board_count : unknown_board_count + 2])
    return players


def calculate_equity(
    hero_cards: list[Card],
    board: list[Card],
    villain_cards: list[list[Card]] | None = None,
    num_opponents: int = 1,
    iterations: int = DEFAULT_ITERATIONS,
    rng: random.Random | None = None,
) -> EquityResult:
    known_villain_hands = villain_cards or []
    _validate_input(hero_cards, board, known_villain_hands, num_opponents)

    unknown_villain = len(known_villain_hands) < num_opponents
    unknown_board_count = 5 - len(board)
    num_players = 1 + num_opponents

    all_known = hero_cards + board + [c for hand in known_villain_hands for c in hand]
    deck = remaining_deck(all_known)

    draw_size = unknown_board_count + (2 if unknown_villain else 0)

    hero_share = 0.0
    opponents_share = [0.0] * num_opponents
    tie_trials = 0
    trials = 0

    def record_outcome(draw: list[Card]) -> None:
        nonlocal hero_share, tie_trials, trials
        full_board = board + draw[:unknown_board_count]
        players = _players_after_deal(hero_cards, known_villain_hands, unknown_villain, draw, unknown_board_count)
        winners = compare_hands(players, full_board)
        share = 1.0 / len(winners)
        if len(winners) > 1:
            tie_trials += 1
        if 0 in winners:
            hero_share += share
        for opp_idx in range(num_opponents):
            player_idx = opp_idx + 1
            if player_idx in winners:
                opponents_share[opp_idx] += share
        trials += 1

    if draw_size == 0:
        # River con tutte le mani già chiuse: confronto diretto, nessun draw.
        record_outcome([])
        method = "direct_comparison"
    elif len(board) == 4 or (len(board) == 5 and draw_size <= 2):
        # Turn (1 carta di board da scoprire, + eventuali 2 carte di un unico
        # avversario ignoto) oppure river con un solo avversario ignoto:
        # il numero di combinazioni residue resta piccolo, enumerazione esatta.
        method = "exact_enumeration"
        for combo in itertools.combinations(deck, draw_size):
            record_outcome(list(combo))
    else:
        # Preflop/flop (o turn con avversario ignoto): Monte Carlo.
        method = "monte_carlo"
        rng = rng or random
        for _ in range(iterations):
            record_outcome(rng.sample(deck, draw_size))

    return EquityResult(
        hero_equity=hero_share / trials,
        opponents_equity=[s / trials for s in opponents_share],
        tie_probability=tie_trials / trials,
        method=method,
        trials=trials,
    )
