from fastapi import APIRouter, HTTPException

from engine.odds import InvalidPotOddsInputError, pot_odds
from api.schemas import PotOddsRequest, PotOddsResponse

router = APIRouter(prefix="/api", tags=["odds"])


@router.post("/pot-odds", response_model=PotOddsResponse)
def post_pot_odds(request: PotOddsRequest) -> PotOddsResponse:
    try:
        required_equity = pot_odds(
            amount_to_call=request.amount_to_call,
            pot_before_call=request.pot_before_call,
        )
    except InvalidPotOddsInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PotOddsResponse(
        required_equity=required_equity,
        required_equity_percentage=required_equity * 100,
    )
