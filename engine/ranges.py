"""Range di mani (es. 'AKs', '77', 'QJo'): parsing ed espansione in combinazioni concrete.

Un range è definito interamente dall'utente (una sua lettura sull'avversario),
non calcolato o suggerito dal motore: resta pura combinatoria, nessun solver.
"""

from __future__ import annotations

import itertools

from engine.cards import RANKS, SUITS, Card


class InvalidRangeError(ValueError):
    pass


def _parse_hand_class(label: str) -> tuple[str, str, str]:
    label = label.strip()
    if len(label) == 2:
        r1, r2 = label[0].upper(), label[1].upper()
        if r1 not in RANKS or r2 not in RANKS:
            raise InvalidRangeError(f"classe non valida: {label!r}")
        if r1 != r2:
            raise InvalidRangeError(f"classe non valida: {label!r} (mancano 's' o 'o' per ranghi diversi)")
        return r1, r2, "pair"

    if len(label) == 3:
        r1, r2, suffix = label[0].upper(), label[1].upper(), label[2].lower()
        if r1 not in RANKS or r2 not in RANKS:
            raise InvalidRangeError(f"classe non valida: {label!r}")
        if r1 == r2:
            raise InvalidRangeError(f"classe non valida: {label!r} (una coppia non ammette 's'/'o')")
        if suffix not in ("s", "o"):
            raise InvalidRangeError(f"suffisso non valido in {label!r} (atteso 's' o 'o')")
        return r1, r2, "suited" if suffix == "s" else "offsuit"

    raise InvalidRangeError(f"formato classe non valido: {label!r} (es. 'AKs', 'QJo', '77')")


def hand_class_combos(label: str) -> list[tuple[Card, Card]]:
    """Tutte le combinazioni di carte concrete per una classe (es. 'AKs' -> 4 combo)."""
    r1, r2, kind = _parse_hand_class(label)

    if kind == "pair":
        return [(Card(r1, s1), Card(r1, s2)) for s1, s2 in itertools.combinations(SUITS, 2)]
    if kind == "suited":
        return [(Card(r1, s), Card(r2, s)) for s in SUITS]
    return [(Card(r1, s1), Card(r2, s2)) for s1 in SUITS for s2 in SUITS if s1 != s2]


def expand_range(labels: list[str], excluded_cards: list[Card]) -> list[tuple[Card, Card]]:
    """Espande un range (lista di classi) in combo concrete, escludendo carte già note.

    Solleva InvalidRangeError se il range è vuoto o se, dopo l'esclusione delle
    carte note (mani proprie/board/altri avversari noti), non resta alcuna
    combinazione utilizzabile.
    """
    if not labels:
        raise InvalidRangeError("il range non può essere vuoto")

    excluded = set(excluded_cards)
    seen: set[frozenset[Card]] = set()
    combos: list[tuple[Card, Card]] = []

    for label in labels:
        for c1, c2 in hand_class_combos(label):
            if c1 in excluded or c2 in excluded:
                continue
            key = frozenset((c1, c2))
            if key in seen:
                continue
            seen.add(key)
            combos.append((c1, c2))

    if not combos:
        raise InvalidRangeError(
            "il range non contiene combinazioni utilizzabili: tutte bloccate dalle carte già note"
        )
    return combos
