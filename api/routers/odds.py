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
        # Soglia effettiva: si calcola solo se l'utente ha davvero stimato delle
        # implied odds, altrimenti coinciderebbe con le pot odds e affollerebbe
        # la schermata con lo stesso numero scritto due volte.
        with_implied = (
            pot_odds(
                amount_to_call=request.amount_to_call,
                pot_before_call=request.pot_before_call,
                implied_future_bet=request.implied_future_bet,
            )
            if request.implied_future_bet > 0
            else None
        )
    except InvalidPotOddsInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PotOddsResponse(
        required_equity=required_equity,
        required_equity_percentage=required_equity * 100,
        required_equity_with_implied=with_implied,
        required_equity_with_implied_percentage=None if with_implied is None else with_implied * 100,
    )
