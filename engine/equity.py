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

from engine.cards import Card, remaining_deck
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

# Quando gli avversari a range sono pochi e stretti, tutte le assegnazioni di mani
# possibili si contano una volta sola: si sa con certezza se i range possono
# coesistere e si pesca direttamente fra quelle valide. Oltre questa soglia i pool
# sono abbastanza larghi da rendere efficiente il rejection sampling.
JOINT_RANGE_MAX_PRODUCT = 100_000

# Tentativi concessi al rejection sampling prima di dichiararlo impraticabile.
# Serve solo per i range troppo larghi da precalcolare: con un tasso di
# accettazione anche solo dell'1% la probabilità di esaurirli è ~10^-44.
MAX_REJECTION_ATTEMPTS = 10_000


class InvalidEquityInputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EquityResult:
    hero_equity: float
    opponents_equity: list[float]
    tie_probability: float  # probabilità che hero divida il piatto, non di uno split qualsiasi
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


def _joint_range_hands(
    range_pools: list[list[tuple[Card, Card]]],
) -> list[tuple[tuple[Card, Card], ...]] | None:
    """Tutte le assegnazioni di una mano per range valide *insieme*, senza carte condivise.

    Restituisce None quando il prodotto dei pool supera JOINT_RANGE_MAX_PRODUCT:
    lì percorrerle tutte costerebbe troppo, ma range così larghi collidono di rado
    e il rejection sampling fa lo stesso lavoro senza materializzare nulla.

    Precalcolarle risolve il problema del rejection sampling con range stretti che
    si bloccano a vicenda: quattro avversari su "AA,KK" hanno 216 assegnazioni
    valide su 20.736, cioè un tentativo accettato ogni 96. Pescare a caso e
    ritentare finisce per esaurire qualsiasi budget di tentativi su almeno uno dei
    20.000 trial, facendo fallire un calcolo che invece è perfettamente possibile.

    Una lista vuota significa impossibile in senso dimostrato, mai "non ci sono
    riuscito": o si sono percorse tutte le assegnazioni senza trovarne una valida,
    o i range non offrono abbastanza carte distinte da servire tutti gli avversari.
    """
    if not range_pools:
        return [()]

    # Prova di impossibilità che non richiede di enumerare nulla: servono due carte
    # distinte per avversario, quindi se l'unione dei range non ne offre abbastanza
    # nessuna assegnazione può esistere. Cinque avversari su "AA,KK" hanno solo otto
    # carte per dieci fabbisogni: si può dirlo subito, anche con pool enormi.
    distinct_cards = {card for pool in range_pools for hand in pool for card in hand}
    if len(distinct_cards) < 2 * len(range_pools):
        return []

    if math.prod(len(pool) for pool in range_pools) > JOINT_RANGE_MAX_PRODUCT:
        return None

    valid: list[tuple[tuple[Card, Card], ...]] = []
    for assignment in itertools.product(*range_pools):
        used: set[Card] = set()
        for hand in assignment:
            used.update(hand)
        if len(used) == 2 * len(assignment):  # nessun avversario usa la carta di un altro
            valid.append(assignment)
    return valid


def _draw_ranged_hands(
    rng: random.Random,
    range_pools: list[list[tuple[Card, Card]]],
    joint_hands: list[tuple[tuple[Card, Card], ...]] | None,
) -> list[list[Card]]:
    """Pesca una mano per ciascun avversario a range.

    In entrambi i rami la distribuzione è la stessa: uniforme sulle assegnazioni
    congiuntamente valide. Non basta pescare dai pool in sequenza filtrando via via
    le carte già uscite — la probabilità di ogni assegnazione finale dipenderebbe
    dall'ordine dei range invece che essere uniforme.
    """
    if joint_hands is not None:
        return [list(hand) for hand in rng.choice(joint_hands)]

    for _ in range(MAX_REJECTION_ATTEMPTS):
        used: set[Card] = set()
        hands: list[list[Card]] = []
        for pool in range_pools:
            c1, c2 = rng.choice(pool)
            if c1 in used or c2 in used:
                break  # collisione: si riparte da capo, non si ripesca solo questo range
            used.add(c1)
            used.add(c2)
            hands.append([c1, c2])
        else:
            return hands

    raise InvalidEquityInputError(
        "i range indicati si bloccano troppo a vicenda perché il campionamento trovi "
        "combinazioni compatibili: allarga i range o riducine il numero"
    )


def _deal_trial(
    rng: random.Random,
    deck: list[Card],
    unknown_board_count: int,
    unknown_random_count: int,
    range_pools: list[list[tuple[Card, Card]]],
    joint_hands: list[tuple[tuple[Card, Card], ...]] | None,
) -> tuple[list[Card], list[list[Card]]]:
    """Pesca le carte di un trial: prima le mani a range, poi il resto.

    Board mancante e avversari a mano ignota si pescano uniformemente da quel che
    resta del mazzo, senza vincoli propri da far collidere con altri.
    """
    ranged_hands = _draw_ranged_hands(rng, range_pools, joint_hands)
    used = {card for hand in ranged_hands for card in hand}

    available = [card for card in deck if card not in used] if used else deck
    needed = unknown_board_count + 2 * unknown_random_count
    drawn = rng.sample(available, needed)
    board_draw = drawn[:unknown_board_count]
    random_hands = [drawn[i : i + 2] for i in range(unknown_board_count, needed, 2)]
    return board_draw, [*ranged_hands, *random_hands]


def _enumeration_size(
    deck_size: int,
    num_range_pools: int,
    joint_hands: list[tuple[tuple[Card, Card], ...]] | None,
    unknown_board_count: int,
    unknown_random_count: int,
) -> float:
    """Quante distribuzioni produrrebbe _enumerate_draws.

    math.inf quando le assegnazioni dei range non sono state precalcolate: quei
    pool sono così larghi che l'enumerazione sarebbe comunque fuori scala.
    Negli altri casi è il conto esatto, non una stima: le assegnazioni valide
    sono già state contate una per una.
    """
    if joint_hands is None:
        return math.inf

    size = len(joint_hands)
    deck_after_hands = deck_size - 2 * num_range_pools
    size *= math.comb(deck_after_hands, unknown_board_count)
    if unknown_random_count == 1:
        size *= math.comb(deck_after_hands - unknown_board_count, 2)
    return size


def _enumerate_draws(
    deck: list[Card],
    joint_hands: list[tuple[tuple[Card, Card], ...]],
    unknown_board_count: int,
    unknown_random_count: int,
) -> Iterator[tuple[list[Card], list[list[Card]]]]:
    """Enumera mani a range, board mancante e mano dell'avversario ignoto.

    Ogni gruppo va pescato in un passaggio annidato distinto, mai da un'unica
    itertools.combinations spezzata per posizione: le combinazioni escono già
    ordinate secondo il mazzo, quindi le prime carte finirebbero sempre sul board
    e le ultime sempre in mano all'avversario. Di ogni insieme di carte si
    enumererebbe una sola ripartizione, sempre la stessa, e l'equity ne uscirebbe
    falsata.

    Le assegnazioni dei range arrivano già filtrate da _joint_range_hands, la
    stessa lista da cui pesca il Monte Carlo: le due strade condividono la
    distribuzione per costruzione invece che per somiglianza fra due filtri
    scritti a parte.

    Gestisce al massimo un avversario a mano ignota: con due o più andrebbe
    enumerata anche l'assegnazione delle coppie ai singoli avversari, e il volume
    supererebbe comunque EXACT_ENUMERATION_MAX_COMBOS finendo in Monte Carlo.
    """
    for ranged_hands in joint_hands:
        used: set[Card] = set()
        for hand in ranged_hands:
            used.update(hand)

        available = [card for card in deck if card not in used] if used else deck
        for board_draw in itertools.combinations(available, unknown_board_count):
            hands = [list(hand) for hand in ranged_hands]
            if unknown_random_count == 0:
                yield list(board_draw), hands
                continue

            on_board = set(board_draw)
            remaining = [card for card in available if card not in on_board]
            for random_hand in itertools.combinations(remaining, 2):
                yield list(board_draw), [*hands, list(random_hand)]


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

    # Una sola volta, prima di qualsiasi trial: quali mani possono avere insieme
    # gli avversari a range. Sia l'enumerazione esatta sia il Monte Carlo pescano
    # da qui, quindi lavorano per costruzione sulla stessa distribuzione.
    joint_range_hands = _joint_range_hands(range_pools)
    if joint_range_hands is not None and not joint_range_hands:
        raise InvalidEquityInputError(
            "i range indicati non possono coesistere: non esiste un'assegnazione di mani che "
            "li rispetti tutti senza che due avversari usino la stessa carta"
        )

    hero_share = 0.0
    hero_share_squares = 0.0  # serve per l'errore standard, vedi più sotto
    opponents_share = [0.0] * num_opponents
    tie_trials = 0
    trials = 0

    def record_outcome(full_board: list[Card], unknown_hands: list[list[Card]]) -> None:
        nonlocal hero_share, hero_share_squares, tie_trials, trials
        players = [hero_cards, *known_villain_hands, *unknown_hands]
        winners = compare_hands(players, full_board)
        share = 1.0 / len(winners)
        if 0 in winners:
            hero_share += share
            hero_share_squares += share * share
            # Solo gli split di cui hero fa parte: un pareggio fra due avversari
            # non è uno split per hero, che quella mano la sta perdendo e basta.
            if len(winners) > 1:
                tie_trials += 1
        for opp_idx in range(num_opponents):
            player_idx = opp_idx + 1
            if player_idx in winners:
                opponents_share[opp_idx] += share
        trials += 1

    if not range_pools and unknown_board_count == 0 and unknown_random_count == 0:
        # River con tutte le mani già chiuse: confronto diretto, nessun draw.
        record_outcome(board, [])
        method = "direct_comparison"
    elif (
        unknown_random_count <= 1
        and joint_range_hands is not None
        and _enumeration_size(
            len(deck), len(range_pools), joint_range_hands, unknown_board_count, unknown_random_count
        )
        <= EXACT_ENUMERATION_MAX_COMBOS
    ):
        # Poche combinazioni residue: le percorriamo tutte una per una, il
        # risultato è la probabilità esatta e non una stima. Vale anche con gli
        # avversari a range, che su turn e river valgono poche centinaia di casi.
        method = "exact_enumeration"
        for board_draw, unknown_hands in _enumerate_draws(
            deck, joint_range_hands, unknown_board_count, unknown_random_count
        ):
            record_outcome(board + board_draw, unknown_hands)
    else:
        # Troppe combinazioni: preflop, 2+ avversari a mano ignota, o range su un
        # board ancora tutto da scoprire. Si stima campionando.
        method = "monte_carlo"
        rng = rng or random
        for _ in range(iterations):
            board_draw, unknown_hands = _deal_trial(
                rng, deck, unknown_board_count, unknown_random_count, range_pools, joint_range_hands
            )
            full_board = board + board_draw
            record_outcome(full_board, unknown_hands)

    if trials == 0:  # rete di sicurezza: nessun percorso deve arrivare qui a mani vuote
        raise InvalidEquityInputError("nessuno scenario valutabile con i dati forniti")

    hero_equity = hero_share / trials
    standard_error = ci_low = ci_high = None
    if method == "monte_carlo":
        # Errore standard della media campionaria, calcolato dalla varianza vera
        # degli esiti invece che con la formula p(1-p) della proporzione: un trial
        # non vale sempre 0 o 1, perché in uno split vale la quota spettante
        # (1/numero_di_vincitori). Con molti split p(1-p) sovrastima la dispersione
        # e restituisce un intervallo più largo del dovuto. Senza split le due
        # formule coincidono. Per i metodi esatti non c'è errore campionario:
        # il risultato è la probabilità esatta, non una stima.
        variance = (hero_share_squares - trials * hero_equity**2) / (trials - 1) if trials > 1 else 0.0
        standard_error = math.sqrt(max(0.0, variance) / trials)
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
