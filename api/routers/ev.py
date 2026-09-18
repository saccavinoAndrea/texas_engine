from fastapi import APIRouter, HTTPException

from engine.ev import InvalidEvInputError, calculate_call_ev
from api.schemas import EvRequest, EvResponse

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
