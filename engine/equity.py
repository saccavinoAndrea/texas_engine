"""Calcolo dell'equity: Monte Carlo su preflop/flop, enumerazione esatta su turn/river.

Gli avversari possono essere: a mano nota (villain_cards), a range noto
(villain_ranges: un sottoinsieme di mani che l'utente stesso definisce,
es. "penso abbia AA-QQ o AKs"), oppure a mano ignota/random. Un range è
sempre fornito dall'utente, mai calcolato dal motore: resta pura
combinatoria, nessun solver GTO.
"""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Iterator
from dataclasses import dataclass

from engine.cards import Card, InvalidCardError, remaining_deck
from engine.evaluator import compare_hands
from engine.ranges import InvalidRangeError, expand_range

DEFAULT_ITERATIONS = 20_000
CONFIDENCE_Z_SCORE = 1.96  # ~95% per una normale, valido per n grande (approssimazione di Wald)

# Oltre questo numero di combinazioni residue l'enumerazione esatta costa più del
# Monte Carlo senza dare un risultato praticamente più utile, quindi si campiona.
# Il caso più pesante che resta esatto è il turn contro un avversario ignoto
# (46 river x 990 mani = 45.540 valutazioni, ~1s); il successivo per dimensione
# sarebbe il flop contro un ignoto, oltre un milione di combinazioni.
EXACT_ENUMERATION_MAX_COMBOS = 50_000


class InvalidEquityInputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EquityResult:
    hero_equity: float
    opponents_equity: list[float]
    tie_probability: float
    method: str
    trials: int
    standard_error: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None


def _validate_input(
    hero_cards: list[Card],
    board: list[Card],
    known_villain_hands: list[list[Card]],
    villain_ranges: list[list[str]],
    num_opponents: int,
) -> None:
    if len(hero_cards) != 2:
        raise InvalidEquityInputError("hero_cards deve contenere esattamente 2 carte")
    if len(board) not in (0, 3, 4, 5):
        raise InvalidEquityInputError("board deve avere 0 (preflop), 3 (flop), 4 (turn) o 5 (river) carte")
    if num_opponents < 1:
        raise InvalidEquityInputError("num_opponents deve essere >= 1")
    if len(known_villain_hands) + len(villain_ranges) > num_opponents:
        raise InvalidEquityInputError(
            "il numero di avversari a mano nota + a range non può superare num_opponents"
        )
    for hand in known_villain_hands:
        if len(hand) != 2:
            raise InvalidEquityInputError("ogni mano avversaria nota deve avere esattamente 2 carte")

    all_known = hero_cards + board + [c for hand in known_villain_hands for c in hand]
    if len(set(all_known)) != len(all_known):
        raise InvalidEquityInputError("carte duplicate tra hero/board/villain")


def _deal_trial(
    rng: random.Random,
    deck: list[Card],
    unknown_board_count: int,
    unknown_random_count: int,
    range_pools: list[list[tuple[Card, Card]]],
    max_attempts: int = 500,
) -> tuple[list[Card], list[list[Card]]]:
    """Pesca le carte di un trial.

    Gli avversari a range vengono pescati con rejection sampling: ognuno pesca
    in modo indipendente e uniforme dal proprio pool intero; se due pool si
    accavallano su una stessa carta, l'intero tentativo viene ritentato. Questo
    è l'unico modo per ottenere una distribuzione uniforme sulle combinazioni
    congiuntamente valide quando i pool si bloccano a vicenda in modo
    asimmetrico — un filtraggio sequenziale (pesca il primo pool, poi filtra
    il secondo sulle carte residue) introdurrebbe un bias: la probabilità di
    ogni combinazione finale dipenderebbe dall'ordine di pesca invece che
    essere uniforme tra le combinazioni congiuntamente compatibili.
    Le carte random (avversari ignoti + board mancante) vengono poi pescate
    uniformemente da quanto resta del mazzo, senza bisogno di rejection
    sampling perché non hanno un pool proprio da far collidere con altri.
    """
    for _ in range(max_attempts):
        used: set[Card] = set()
        ranged_hands: list[list[Card]] = []
        conflict = False

        for pool in range_pools:
            c1, c2 = rng.choice(pool)
            if c1 in used or c2 in used:
                conflict = True
                break
            used.add(c1)
            used.add(c2)
            ranged_hands.append([c1, c2])

        if conflict:
            continue

        available = [card for card in deck if card not in used]
        needed = unknown_board_count + 2 * unknown_random_count
        drawn = rng.sample(available, needed)
        board_draw = drawn[:unknown_board_count]
        random_hands = [drawn[i : i + 2] for i in range(unknown_board_count, needed, 2)]
        return board_draw, [*ranged_hands, *random_hands]

    raise InvalidEquityInputError(
        "impossibile pescare mani valide per i range indicati: troppo vincolati rispetto alle carte note"
    )


def _enumeration_size(deck_size: int, unknown_board_count: int, unknown_random_count: int) -> int:
    """Quante distribuzioni distinte produrrebbe _enumerate_draws."""
    size = math.comb(deck_size, unknown_board_count)
    if unknown_random_count == 1:
        size *= math.comb(deck_size - unknown_board_count, 2)
    return size


def _enumerate_draws(
    deck: list[Card],
    unknown_board_count: int,
    unknown_random_count: int,
) -> Iterator[tuple[list[Card], list[list[Card]]]]:
    """Enumera le carte di board mancanti e la mano dell'avversario ignoto.

    I due gruppi vanno pescati in due passaggi annidati e non da un'unica
    itertools.combinations spezzata per posizione: le combinazioni escono già
    ordinate secondo il mazzo, quindi le prime carte finirebbero sempre sul board
    e le ultime sempre in mano all'avversario. Di ogni insieme di carte si
    enumererebbe una sola delle ripartizioni possibili, sempre la stessa (con una
    carta di board e due di mano, un caso su tre), e l'equity ne uscirebbe falsata.

    Gestisce al massimo un avversario a mano ignota: con due o più andrebbe
    enumerata anche l'assegnazione delle coppie ai singoli avversari, e il volume
    supererebbe comunque EXACT_ENUMERATION_MAX_COMBOS finendo in Monte Carlo.
    """
    for board_draw in itertools.combinations(deck, unknown_board_count):
        if unknown_random_count == 0:
            yield list(board_draw), []
            continue

        on_board = set(board_draw)
        remaining = [card for card in deck if card not in on_board]
        for hand in itertools.combinations(remaining, 2):
            yield list(board_draw), [list(hand)]


def calculate_equity(
    hero_cards: list[Card],
    board: list[Card],
    villain_cards: list[list[Card]] | None = None,
    villain_ranges: list[list[str]] | None = None,
    num_opponents: int = 1,
    iterations: int = DEFAULT_ITERATIONS,
    rng: random.Random | None = None,
) -> EquityResult:
    known_villain_hands = villain_cards or []
    ranges = villain_ranges or []
    _validate_input(hero_cards, board, known_villain_hands, ranges, num_opponents)

    unknown_random_count = num_opponents - len(known_villain_hands) - len(ranges)
    unknown_board_count = 5 - len(board)

    all_known = hero_cards + board + [c for hand in known_villain_hands for c in hand]
    deck = remaining_deck(all_known)

    try:
        range_pools = [expand_range(labels, all_known) for labels in ranges]
    except InvalidRangeError as exc:
        raise InvalidEquityInputError(str(exc)) from exc

    hero_share = 0.0
    opponents_share = [0.0] * num_opponents
    tie_trials = 0
    trials = 0

    def record_outcome(full_board: list[Card], unknown_hands: list[list[Card]]) -> None:
        nonlocal hero_share, tie_trials, trials
        players = [hero_cards, *known_villain_hands, *unknown_hands]
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

    if not ranges and unknown_board_count == 0 and unknown_random_count == 0:
        # River con tutte le mani già chiuse: confronto diretto, nessun draw.
        record_outcome(board, [])
        method = "direct_comparison"
    elif (
        not ranges
        and unknown_random_count <= 1
        and _enumeration_size(len(deck), unknown_board_count, unknown_random_count)
        <= EXACT_ENUMERATION_MAX_COMBOS
    ):
        # Poche combinazioni residue: le percorriamo tutte una per una, il
        # risultato è la probabilità esatta e non una stima.
        method = "exact_enumeration"
        for board_draw, unknown_hands in _enumerate_draws(deck, unknown_board_count, unknown_random_count):
            record_outcome(board + board_draw, unknown_hands)
    else:
        # Troppe combinazioni (preflop, o 2+ avversari a mano ignota), oppure
        # avversari a range: Monte Carlo (l'enumerazione esatta con i range
        # richiederebbe una gestione combinatoria dedicata).
        method = "monte_carlo"
        rng = rng or random
        for _ in range(iterations):
            board_draw, unknown_hands = _deal_trial(rng, deck, unknown_board_count, unknown_random_count, range_pools)
            full_board = board + board_draw
            record_outcome(full_board, unknown_hands)

    hero_equity = hero_share / trials
    standard_error = ci_low = ci_high = None
    if method == "monte_carlo":
        # Approssimazione di Wald sulla proporzione stimata: valida perché il
        # Monte Carlo usa già migliaia di iterazioni (n grande). Per i metodi
        # esatti (direct_comparison/exact_enumeration) non c'è errore campionario:
        # il risultato è la probabilità esatta, non una stima.
        standard_error = math.sqrt(hero_equity * (1 - hero_equity) / trials)
        ci_low = max(0.0, hero_equity - CONFIDENCE_Z_SCORE * standard_error)
        ci_high = min(1.0, hero_equity + CONFIDENCE_Z_SCORE * standard_error)

    return EquityResult(
        hero_equity=hero_equity,
        opponents_equity=[s / trials for s in opponents_share],
        tie_probability=tie_trials / trials,
        method=method,
        trials=trials,
        standard_error=standard_error,
        ci_low=ci_low,
        ci_high=ci_high,
    )
