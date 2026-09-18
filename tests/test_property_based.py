"""Test basati su proprietà (Hypothesis): invarianti che devono valere per QUALSIASI
input valido, non solo per gli scenari scelti a mano.

I test "a esempio" del resto della suite sono ciechi a una classe di bug: un errore
che si manifesta solo per certe combinazioni di piatto/puntata/carte che nessuno ha
pensato di scrivere a mano. Qui Hypothesis genera centinaia di input diversi e
verifica proprietà che devono restare vere sempre, per esempio:

- le equity di tutti i giocatori devono sommare esattamente a 1
- l'EV di una chiamata è una funzione monotona crescente dell'equity
- l'MDF è sempre compreso tra 0 e 1
- riordinare le carte in mano non cambia la forza della mano

Quando un test qui fallisce, Hypothesis restituisce anche il controesempio minimo
che l'ha fatto fallire (shrinking): è quello da riprodurre a mano per capire il bug.
"""

from __future__ import annotations

import itertools
import random

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from engine.cards import RANKS, Card, full_deck, remaining_deck
from engine.equity import (
    JOINT_RANGE_MAX_PRODUCT,
    InvalidEquityInputError,
    _joint_range_hands,
    calculate_equity,
)
from engine.evaluator import compare_hands, hand_rank
from engine.ev import calculate_call_ev, calculate_shove_ev
from engine.metrics import calculate_max_implied_bet, calculate_mdf, calculate_spr
from engine.odds import pot_odds
from engine.ranges import expand_range, hand_class_combos

settings.register_profile(
    "engine",
    deadline=None,  # l'enumerazione esatta e i Monte Carlo superano facilmente i 200ms di default
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
settings.load_profile("engine")

DECK = full_deck()
POSITIVE_MONEY = st.floats(min_value=0.0, max_value=1_000_000, allow_nan=False, allow_infinity=False)
UNIT_INTERVAL = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


@st.composite
def distinct_cards(draw, n: int) -> list[Card]:
    return draw(st.lists(st.sampled_from(DECK), min_size=n, max_size=n, unique=True))


# --------------------------------------------------------------------------
# engine.cards
# --------------------------------------------------------------------------


@given(distinct_cards(5))
def test_remaining_deck_size_matches_known_cards(known):
    assert len(remaining_deck(known)) == 52 - len(known)
    assert set(remaining_deck(known)).isdisjoint(known)


# --------------------------------------------------------------------------
# engine.evaluator
# --------------------------------------------------------------------------


@given(distinct_cards(7))
def test_hand_rank_does_not_depend_on_hole_card_order(cards):
    hole, board = cards[:2], cards[2:]
    assert hand_rank(hole, board) == hand_rank([hole[1], hole[0]], board)


@given(distinct_cards(11))  # board(5) + 3 giocatori a 2 carte
def test_compare_hands_winners_are_invariant_to_player_order(cards):
    board = cards[:5]
    players = [cards[5:7], cards[7:9], cards[9:11]]

    winners_original = set(compare_hands(players, board))

    shuffled_order = [2, 0, 1]
    shuffled_players = [players[i] for i in shuffled_order]
    winners_shuffled = compare_hands(shuffled_players, board)
    # Rimappa gli indici vincenti sulla posizione originale: devono essere lo stesso insieme.
    winners_remapped = {shuffled_order[i] for i in winners_shuffled}

    assert winners_remapped == winners_original


@given(distinct_cards(7))
def test_compare_hands_agrees_with_hand_rank_on_two_players(cards):
    hole1, hole2, board = cards[:2], cards[2:4], cards[4:]
    r1, r2 = hand_rank(hole1, board), hand_rank(hole2, board)
    winners = compare_hands([hole1, hole2], board)
    if r1 < r2:
        assert winners == [0]
    elif r2 < r1:
        assert winners == [1]
    else:
        assert winners == [0, 1]


# --------------------------------------------------------------------------
# engine.ranges
# --------------------------------------------------------------------------


@given(st.sampled_from(RANKS))
def test_pair_class_always_has_six_combos(rank):
    assert len(hand_class_combos(f"{rank}{rank}")) == 6


@given(st.sampled_from(RANKS), st.sampled_from(RANKS))
def test_suited_and_offsuit_combo_counts_are_fixed(r1, r2):
    assume(r1 != r2)
    assert len(hand_class_combos(f"{r1}{r2}s")) == 4
    assert len(hand_class_combos(f"{r1}{r2}o")) == 12


@given(st.sampled_from(RANKS), st.sampled_from(RANKS), st.sampled_from(["s", "o"]))
def test_combos_never_pair_a_card_with_itself(r1, r2, suffix):
    assume(r1 != r2)
    for c1, c2 in hand_class_combos(f"{r1}{r2}{suffix}"):
        assert c1 != c2


@given(distinct_cards(4))
def test_more_blockers_never_increase_combo_count(cards):
    """Aggiungere carte note può solo eliminare combinazioni, mai crearne."""
    labels = ["AA", "KK", "AKs"]
    with_0 = expand_range_count(labels, [])
    with_1 = expand_range_count(labels, cards[:1])
    with_4 = expand_range_count(labels, cards)
    assert with_4 <= with_1 <= with_0


def expand_range_count(labels: list[str], excluded: list[Card]) -> int:
    from engine.ranges import count_range_combos

    return count_range_combos(labels, excluded)


# --------------------------------------------------------------------------
# engine.odds / engine.ev — l'incrocio fra le due funzioni deve reggere ovunque
# --------------------------------------------------------------------------


@given(POSITIVE_MONEY, POSITIVE_MONEY, POSITIVE_MONEY)
def test_pot_odds_result_is_always_a_probability(amount_to_call, pot_before_call, implied):
    required = pot_odds(amount_to_call, pot_before_call, implied)
    assert 0.0 <= required <= 1.0


@given(
    pot=st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False),
    call=st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False),
    implied=POSITIVE_MONEY,
)
def test_pot_odds_threshold_is_exactly_the_call_ev_break_even_point(pot, call, implied):
    """Il numero che pot_odds chiama 'equity richiesta' deve essere lo stesso punto
    in cui calculate_call_ev vale zero: sono la stessa soglia vista da due funzioni,
    e se divergono i due riquadri dell'app raccontano cose diverse (il bug del
    sesto giro, qui esteso a tutto il dominio invece che a un solo esempio)."""
    threshold = pot_odds(call, pot, implied)
    ev_at_threshold = calculate_call_ev(threshold, call, pot, implied)
    assert ev_at_threshold == pytest.approx(0.0, abs=1e-6)


@given(
    call=POSITIVE_MONEY,
    pot=POSITIVE_MONEY,
    implied=POSITIVE_MONEY,
    e1=UNIT_INTERVAL,
    e2=UNIT_INTERVAL,
)
def test_call_ev_is_monotonic_increasing_in_equity(call, pot, implied, e1, e2):
    assume(e1 <= e2)
    ev1 = calculate_call_ev(e1, call, pot, implied)
    ev2 = calculate_call_ev(e2, call, pot, implied)
    assert ev1 <= ev2 + 1e-9


@given(
    equity=UNIT_INTERVAL,
    fold_probability=UNIT_INTERVAL,
    pot=POSITIVE_MONEY,
    shove=st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False),
)
def test_shove_ev_is_a_convex_combination_of_fold_and_call_outcomes(equity, fold_probability, pot, shove):
    """EV = P(fold)*ev_fold + P(call)*ev_call è una combinazione convessa: deve
    sempre cadere fra i due estremi, mai fuori."""
    ev = calculate_shove_ev(equity, fold_probability, pot, shove)
    ev_if_fold = pot
    ev_if_called = equity * (pot + 2 * shove) - shove
    low, high = min(ev_if_fold, ev_if_called), max(ev_if_fold, ev_if_called)
    assert low - 1e-6 <= ev <= high + 1e-6


@given(
    equity=UNIT_INTERVAL,
    pot=POSITIVE_MONEY,
    shove=st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False),
    fp1=UNIT_INTERVAL,
    fp2=UNIT_INTERVAL,
)
def test_shove_ev_moves_toward_fold_outcome_as_fold_probability_grows(equity, pot, shove, fp1, fp2):
    """Più fold equity si stima, più il risultato deve avvicinarsi a 'vinco il piatto
    attuale': la funzione è lineare in fold_probability, quindi il verso è sempre lo
    stesso quando ev_if_fold >= ev_if_called (il caso interessante e comune: shove
    profittevole solo grazie alla fold equity)."""
    assume(fp1 <= fp2)
    ev_if_called = equity * (pot + 2 * shove) - shove
    assume(pot >= ev_if_called)  # solo il verso "più fold aiuta": l'altro verso è speculare
    ev1 = calculate_shove_ev(equity, fp1, pot, shove)
    ev2 = calculate_shove_ev(equity, fp2, pot, shove)
    assert ev1 <= ev2 + 1e-9


# --------------------------------------------------------------------------
# engine.metrics
# --------------------------------------------------------------------------


@given(
    stack=st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False),
    pot=st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False),
)
def test_spr_matches_its_definition(stack, pot):
    assert calculate_spr(stack, pot) == pytest.approx(stack / pot)


@given(
    pot_before_call=st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False),
    call_fraction=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False),
)
def test_mdf_is_always_a_probability(pot_before_call, call_fraction):
    amount_to_call = pot_before_call * call_fraction  # rispetta amount_to_call <= pot_before_call
    mdf = calculate_mdf(pot_before_call, amount_to_call)
    assert 0.0 <= mdf <= 1.0


@given(
    pot_before_call=st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False),
    call_fraction=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False),
)
def test_mdf_matches_the_pre_bet_pot_definition_across_the_whole_domain(pot_before_call, call_fraction):
    """La conversione fra 'piatto che comprende la puntata' (convenzione dell'app) e
    'piatto prima della puntata' (convenzione dei manuali) deve reggere ovunque, non
    solo sull'esempio del terzo giro dove era stata trovata cablata male."""
    amount_to_call = pot_before_call * call_fraction
    pot_before_bet = pot_before_call - amount_to_call

    mdf = calculate_mdf(pot_before_call, amount_to_call)
    textbook = pot_before_bet / (pot_before_bet + amount_to_call) if (pot_before_bet + amount_to_call) > 0 else 1.0

    assert mdf == pytest.approx(textbook, abs=1e-9)


@given(stack=POSITIVE_MONEY, amount_to_call=POSITIVE_MONEY)
def test_max_implied_bet_is_never_negative(stack, amount_to_call):
    assert calculate_max_implied_bet(stack, amount_to_call) >= 0.0


# --------------------------------------------------------------------------
# engine.equity — il cuore del motore
# --------------------------------------------------------------------------


@st.composite
def equity_scenarios(draw):
    """Uno scenario valido e casuale: hero + board (0/3/4/5 carte) + 0-2 avversari
    a mano nota, senza sovrapposizioni. num_opponents copre anche avversari ignoti."""
    board_len = draw(st.sampled_from([0, 3, 4, 5]))
    num_known = draw(st.integers(min_value=0, max_value=2))
    num_opponents = draw(st.integers(min_value=max(1, num_known), max_value=num_known + 2))

    cards = draw(distinct_cards(2 + board_len + 2 * num_known))
    hero = cards[:2]
    idx = 2
    board = cards[idx : idx + board_len]
    idx += board_len
    known = [cards[i : i + 2] for i in range(idx, idx + 2 * num_known, 2)]

    return hero, board, known, num_opponents


@settings(max_examples=50)
@given(equity_scenarios(), st.integers(min_value=0, max_value=2**31 - 1))
def test_equities_always_sum_to_one_and_stay_bounded(scenario, seed):
    hero, board, known, num_opponents = scenario
    result = calculate_equity(
        hero, board, villain_cards=known or None, num_opponents=num_opponents,
        iterations=2000, rng=random.Random(seed),
    )

    assert 0.0 <= result.hero_equity <= 1.0
    for equity in result.opponents_equity:
        assert 0.0 <= equity <= 1.0
    assert result.hero_equity + sum(result.opponents_equity) == pytest.approx(1.0, abs=1e-9)
    assert 0.0 <= result.tie_probability <= 1.0

    if result.ci_low is not None:
        assert result.ci_low <= result.hero_equity <= result.ci_high
        assert 0.0 <= result.ci_low
        assert result.ci_high <= 1.0
    else:
        assert result.standard_error is None and result.ci_high is None


@settings(max_examples=40)
@given(equity_scenarios())
def test_exact_methods_are_independent_of_the_rng(scenario):
    """direct_comparison ed exact_enumeration non campionano: il risultato non deve
    dipendere da quale generatore casuale (o quale seed) viene passato."""
    hero, board, known, num_opponents = scenario

    result_a = calculate_equity(
        hero, board, villain_cards=known or None, num_opponents=num_opponents,
        iterations=2000, rng=random.Random(1),
    )
    result_b = calculate_equity(
        hero, board, villain_cards=known or None, num_opponents=num_opponents,
        iterations=2000, rng=random.Random(987654),
    )

    if result_a.method != "monte_carlo":
        assert result_a == result_b


@settings(max_examples=25)
@given(equity_scenarios())
def test_monte_carlo_is_reproducible_with_the_same_seed(scenario):
    hero, board, known, num_opponents = scenario

    result_a = calculate_equity(
        hero, board, villain_cards=known or None, num_opponents=num_opponents,
        iterations=1500, rng=random.Random(42),
    )
    result_b = calculate_equity(
        hero, board, villain_cards=known or None, num_opponents=num_opponents,
        iterations=1500, rng=random.Random(42),
    )

    assert result_a == result_b


RANGE_LABEL_POOL = ["AA", "KK", "QQ", "JJ", "AKs", "AKo", "AQo", "KQo"]


@st.composite
def equity_scenarios_with_ranges(draw):
    board_len = draw(st.sampled_from([0, 3, 4, 5]))
    num_range_opponents = draw(st.integers(min_value=1, max_value=2))
    num_opponents = draw(st.integers(min_value=num_range_opponents, max_value=num_range_opponents + 1))

    cards = draw(distinct_cards(2 + board_len))
    hero, board = cards[:2], cards[2:]

    range_labels = draw(
        st.lists(
            st.lists(st.sampled_from(RANGE_LABEL_POOL), min_size=1, max_size=2, unique=True),
            min_size=num_range_opponents,
            max_size=num_range_opponents,
        )
    )
    return hero, board, range_labels, num_opponents


@settings(max_examples=25)
@given(equity_scenarios_with_ranges())
def test_equity_with_villain_ranges_still_sums_to_one(scenario):
    hero, board, range_labels, num_opponents = scenario
    try:
        result = calculate_equity(
            hero, board, villain_ranges=range_labels, num_opponents=num_opponents,
            iterations=1500, rng=random.Random(0),
        )
    except InvalidEquityInputError:
        # Range che si bloccano a vicenda date le carte pescate: input legittimo che
        # il motore respinge correttamente, non è quello che questo test verifica.
        assume(False)
        return

    assert 0.0 <= result.hero_equity <= 1.0
    total = result.hero_equity + sum(result.opponents_equity)
    assert total == pytest.approx(1.0, abs=1e-9)


@given(st.integers(min_value=1, max_value=4))
def test_aa_kk_ranges_stay_feasible_up_to_four_opponents(num_opponents):
    """Regressione del quinto giro estesa a tutta la fascia: 4 avversari su AA/KK
    usano esattamente le 8 carte disponibili (2 ranghi x 4 semi), quindi restano
    giocabili; il test lo verifica per 1, 2, 3 e 4 avversari, non solo per 4."""
    pools = [expand_range(["AA", "KK"], []) for _ in range(num_opponents)]
    joint = _joint_range_hands(pools)
    assert joint is not None
    assert len(joint) > 0


@given(st.integers(min_value=5, max_value=8))
def test_aa_kk_ranges_are_impossible_from_five_opponents(num_opponents):
    """Da 5 avversari servirebbero 10 carte distinte da un pool che ne offre 8."""
    pools = [expand_range(["AA", "KK"], []) for _ in range(num_opponents)]
    assert _joint_range_hands(pools) == []


@settings(max_examples=30)
@given(
    st.lists(
        st.lists(st.sampled_from(RANGE_LABEL_POOL), min_size=1, max_size=2, unique=True),
        min_size=1,
        max_size=3,
    )
)
def test_joint_range_hands_matches_brute_force_enumeration(range_labels):
    """_joint_range_hands è la lista da cui pescano sia l'enumerazione esatta sia il
    Monte Carlo: deve coincidere esattamente con un'enumerazione indipendente scritta
    qui, per un campione ampio di combinazioni di range casuali."""
    pools = [expand_range(labels, []) for labels in range_labels]
    joint = _joint_range_hands(pools)

    product = 1
    for pool in pools:
        product *= len(pool)

    if product > JOINT_RANGE_MAX_PRODUCT:
        assert joint is None
        return

    expected = []
    for assignment in itertools.product(*pools):
        used: set[Card] = set()
        for hand in assignment:
            used.update(hand)
        if len(used) == 2 * len(assignment):
            expected.append(assignment)

    def key(assignment):
        return tuple(sorted(frozenset(hand) for hand in [frozenset(h) for h in assignment]))

    assert sorted(map(key, joint), key=str) == sorted(map(key, expected), key=str)
