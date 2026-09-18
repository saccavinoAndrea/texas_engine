from fastapi import APIRouter, HTTPException

from engine.ev import InvalidEvInputError, calculate_call_ev, calculate_shove_ev
from api.schemas import EvRequest, EvResponse, ShoveEvRequest, ShoveEvResponse

router = APIRouter(prefix="/api", tags=["ev"])


@router.post("/ev", response_model=EvResponse)
def post_ev(request: EvRequest) -> EvResponse:
    try:
        ev = calculate_call_ev(
            hero_equity=request.hero_equity,
            amount_to_call=request.amount_to_call,
            pot_before_call=request.pot_before_call,
        )
    except InvalidEvInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return EvResponse(ev=ev, profitable=ev > 0)


@router.post("/shove-ev", response_model=ShoveEvResponse)
def post_shove_ev(request: ShoveEvRequest) -> ShoveEvResponse:
    try:
        ev = calculate_shove_ev(
            hero_equity_if_called=request.hero_equity_if_called,
            fold_probability=request.fold_probability,
            pot_before_shove=request.pot_before_shove,
            shove_amount=request.shove_amount,
        )
    except InvalidEvInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ShoveEvResponse(ev=ev, profitable=ev > 0)
