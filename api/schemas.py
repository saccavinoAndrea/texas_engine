"""Modelli Pydantic per le richieste/risposte dell'API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from engine.cards import Card, InvalidCardError
from engine.equity import DEFAULT_ITERATIONS


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


class EquityResponse(BaseModel):
    hero_equity: float
    opponents_equity: list[float]
    tie_probability: float
    method: str
    trials: int


class PotOddsRequest(BaseModel):
    amount_to_call: float = Field(..., ge=0)
    pot_before_call: float = Field(..., ge=0)


class PotOddsResponse(BaseModel):
    required_equity: float
    required_equity_percentage: float
