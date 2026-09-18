from fastapi import APIRouter

from engine.cards import parse_cards
from engine.ranges import count_range_combos
from api.schemas import RangeComboCountRequest, RangeComboCountResponse

router = APIRouter(prefix="/api", tags=["ranges"])


@router.post("/range-combo-count", response_model=RangeComboCountResponse)
def post_range_combo_count(request: RangeComboCountRequest) -> RangeComboCountResponse:
    known_cards = parse_cards(request.known_cards)
    combo_count = count_range_combos(request.labels, known_cards)
    return RangeComboCountResponse(combo_count=combo_count)
