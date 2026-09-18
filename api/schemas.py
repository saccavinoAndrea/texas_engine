"""Modelli Pydantic per le richieste/risposte dell'API."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from engine.cards import Card, InvalidCardError
from engine.equity import DEFAULT_ITERATIONS
from engine.ranges import InvalidRangeError, hand_class_combos


class _EquityBoundsMixin(BaseModel):
    """Estremi dell'intervallo di confidenza sull'equity, comuni a EV e shove EV.

    Vanno o entrambi o nessuno dei due, e in ordine: invertiti non farebbero
    fallire nulla, ma il controllo "l'intervallo contiene lo zero" risulterebbe
    sempre falso e il verdetto tornerebbe a dirsi certo dove non lo è.
    """

    hero_equity_low: float | None = Field(
        default=None, ge=0, le=1, description="Estremo inferiore dell'IC 95% sull'equity (solo Monte Carlo)."
    )
    hero_equity_high: float | None = Field(
        default=None, ge=0, le=1, description="Estremo superiore dell'IC 95% sull'equity (solo Monte Carlo)."
    )

    @model_validator(mode="after")
    def _check_equity_bounds(self) -> Self:
        if (self.hero_equity_low is None) != (self.hero_equity_high is None):
            raise ValueError("hero_equity_low e hero_equity_high vanno forniti insieme")
        if (
            self.hero_equity_low is not None
            and self.hero_equity_high is not None
            and self.hero_equity_low > self.hero_equity_high
        ):
            raise ValueError("hero_equity_low non può superare hero_equity_high")
        return self


def _validate_card_code(code: str) -> str:
    try:
        Card.parse(code)
    except InvalidCardError as exc:
        raise ValueError(str(exc)) from exc
    return code


class EquityRequest(BaseModel):
    hero_cards: list[str] = Field(..., min_length=2, max_length=2, examples=[["Ah", "Kh"]])
    board: list[str] = Field(default_factory=list, examples=[["Jh", "9h", "2c"]])
    villain_cards: list[list[str]] | None = Field(
        default=None,
        description="Mani avversarie note (0..num_opponents). Gli avversari non specificati sono mano ignota/random.",
    )
    villain_ranges: list[list[str]] | None = Field(
        default=None,
        description="Range per altri avversari (es. [['AA','KK','AKs']]), assegnati dopo quelli a mano nota.",
    )
    num_opponents: int = Field(default=1, ge=1, le=8)
    iterations: int = Field(default=DEFAULT_ITERATIONS, ge=1000, le=200_000)

    @field_validator("hero_cards")
    @classmethod
    def _validate_hero_cards(cls, value: list[str]) -> list[str]:
        return [_validate_card_code(c) for c in value]

    @field_validator("board")
    @classmethod
    def _validate_board(cls, value: list[str]) -> list[str]:
        if len(value) not in (0, 3, 4, 5):
            raise ValueError("board deve avere 0, 3, 4 o 5 carte")
        return [_validate_card_code(c) for c in value]

    @field_validator("villain_cards")
    @classmethod
    def _validate_villain_cards(cls, value: list[list[str]] | None) -> list[list[str]] | None:
        if value is None:
            return None
        for hand in value:
            if len(hand) != 2:
                raise ValueError("ogni mano avversaria deve avere esattamente 2 carte")
            for c in hand:
                _validate_card_code(c)
        return value

    @field_validator("villain_ranges")
    @classmethod
    def _validate_villain_ranges(cls, value: list[list[str]] | None) -> list[list[str]] | None:
        if value is None:
            return None
        for labels in value:
            if not labels:
                raise ValueError("ogni range deve contenere almeno una classe di mano")
            for label in labels:
                try:
                    hand_class_combos(label)
                except InvalidRangeError as exc:
                    raise ValueError(str(exc)) from exc
        return value


class EquityResponse(BaseModel):
    hero_equity: float
    opponents_equity: list[float]
    tie_probability: float
    method: str
    trials: int
    standard_error: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None


class PotOddsRequest(BaseModel):
    amount_to_call: float = Field(..., ge=0)
    pot_before_call: float = Field(..., ge=0)
    implied_future_bet: float = Field(
        default=0.0,
        ge=0,
        description="Stima manuale di puntate future incassate vincendo lo showdown: abbassa la soglia di pareggio.",
    )


class PotOddsResponse(BaseModel):
    required_equity: float
    required_equity_percentage: float
    required_equity_with_implied: float | None = Field(
        default=None,
        description="Soglia di pareggio che tiene conto delle implied odds; null se non ne sono state indicate.",
    )
    required_equity_with_implied_percentage: float | None = None


class EvRequest(_EquityBoundsMixin):
    hero_equity: float = Field(..., ge=0, le=1)
    amount_to_call: float = Field(..., ge=0)
    pot_before_call: float = Field(..., ge=0)
    implied_future_bet: float = Field(
        default=0.0, ge=0, description="Stima manuale di puntate future vinte in caso di showdown vinto (implied odds)."
    )


class EvResponse(BaseModel):
    ev: float
    profitable: bool
    ev_low: float | None = None
    ev_high: float | None = None


class ShoveEvRequest(_EquityBoundsMixin):
    hero_equity_if_called: float = Field(..., ge=0, le=1)
    fold_probability: float = Field(..., ge=0, le=1)
    pot_before_shove: float = Field(..., ge=0)
    shove_amount: float = Field(..., ge=0)
    villain_already_in: float = Field(
        default=0.0,
        ge=0,
        description="Quanto l'avversario ha già messo nel piatto in questo giro (l'importo che si dovrebbe chiamare): è già dentro pot_before_shove e non va contato due volte.",
    )


class ShoveEvResponse(BaseModel):
    ev: float
    profitable: bool
    ev_low: float | None = None
    ev_high: float | None = None


class TableMetricsRequest(BaseModel):
    effective_stack: float = Field(..., ge=0)
    pot_before_call: float = Field(..., ge=0)
    amount_to_call: float = Field(..., ge=0)


class TableMetricsResponse(BaseModel):
    spr: float | None
    mdf: float | None
    max_implied_bet: float


class RangeComboCountRequest(BaseModel):
    labels: list[str] = Field(default_factory=list)
    known_cards: list[str] = Field(default_factory=list)

    @field_validator("labels")
    @classmethod
    def _validate_labels(cls, value: list[str]) -> list[str]:
        for label in value:
            try:
                hand_class_combos(label)
            except InvalidRangeError as exc:
                raise ValueError(str(exc)) from exc
        return value

    @field_validator("known_cards")
    @classmethod
    def _validate_known_cards(cls, value: list[str]) -> list[str]:
        return [_validate_card_code(c) for c in value]


class RangeComboCountResponse(BaseModel):
    combo_count: int
