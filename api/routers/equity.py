from fastapi import APIRouter, HTTPException

from engine.cards import parse_cards
from engine.equity import InvalidEquityInputError, calculate_equity
from api.schemas import EquityRequest, EquityResponse

router = APIRouter(prefix="/api", tags=["equity"])


@router.post("/equity", response_model=EquityResponse)
def post_equity(request: EquityRequest) -> EquityResponse:
    hero_cards = parse_cards(request.hero_cards)
    board = parse_cards(request.board)
    villain_cards = (
        [parse_cards(hand) for hand in request.villain_cards] if request.villain_cards else None
    )

    try:
        result = calculate_equity(
            hero_cards=hero_cards,
            board=board,
            villain_cards=villain_cards,
            num_opponents=request.num_opponents,
            iterations=request.iterations,
        )
    except InvalidEquityInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return EquityResponse(
        hero_equity=result.hero_equity,
        opponents_equity=result.opponents_equity,
        tie_probability=result.tie_probability,
        method=result.method,
        trials=result.trials,
    )
