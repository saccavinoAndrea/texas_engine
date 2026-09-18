from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from engine.ev import InvalidEvInputError, calculate_call_ev, calculate_shove_ev
from api.schemas import EvRequest, EvResponse, ShoveEvRequest, ShoveEvResponse

router = APIRouter(prefix="/api", tags=["ev"])


def _ev_bounds(
    equity_low: float | None,
    equity_high: float | None,
    ev_at: Callable[[float], float],
) -> tuple[float | None, float | None]:
    """Traduce l'intervallo di confidenza sull'equity in un intervallo sull'EV.

    L'EV è una funzione crescente dell'equity (entrambe le formule la moltiplicano
    per un piatto non negativo), quindi gli estremi si mappano uno a uno senza
    doverli riordinare. Serve perché un EV stimato via Monte Carlo può avere un
    segno incerto: se l'intervallo attraversa lo zero, dire "call profittevole"
    sarebbe dare per certo qualcosa che il campionamento non ha stabilito.

    Gli estremi arrivano solo dai metodi campionati: con l'enumerazione esatta
    l'equity è la probabilità vera e non c'è nessun intervallo da propagare.
    """
    if equity_low is None or equity_high is None:
        return None, None
    return ev_at(equity_low), ev_at(equity_high)


@router.post("/ev", response_model=EvResponse)
def post_ev(request: EvRequest) -> EvResponse:
    def ev_at(equity: float) -> float:
        return calculate_call_ev(
            hero_equity=equity,
            amount_to_call=request.amount_to_call,
            pot_before_call=request.pot_before_call,
            implied_future_bet=request.implied_future_bet,
        )

    try:
        ev = ev_at(request.hero_equity)
        ev_low, ev_high = _ev_bounds(request.hero_equity_low, request.hero_equity_high, ev_at)
    except InvalidEvInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return EvResponse(ev=ev, profitable=ev > 0, ev_low=ev_low, ev_high=ev_high)


@router.post("/shove-ev", response_model=ShoveEvResponse)
def post_shove_ev(request: ShoveEvRequest) -> ShoveEvResponse:
    def ev_at(equity: float) -> float:
        return calculate_shove_ev(
            hero_equity_if_called=equity,
            fold_probability=request.fold_probability,
            pot_before_shove=request.pot_before_shove,
            shove_amount=request.shove_amount,
            villain_already_in=request.villain_already_in,
        )

    try:
        ev = ev_at(request.hero_equity_if_called)
        ev_low, ev_high = _ev_bounds(request.hero_equity_low, request.hero_equity_high, ev_at)
    except InvalidEvInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ShoveEvResponse(ev=ev, profitable=ev > 0, ev_low=ev_low, ev_high=ev_high)
