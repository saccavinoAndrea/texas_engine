from fastapi import APIRouter

from engine.metrics import InvalidMetricsInputError, calculate_mdf, calculate_spr
from api.schemas import TableMetricsRequest, TableMetricsResponse

router = APIRouter(prefix="/api", tags=["metrics"])


@router.post("/table-metrics", response_model=TableMetricsResponse)
def post_table_metrics(request: TableMetricsRequest) -> TableMetricsResponse:
    # spr e mdf sono informazioni accessorie indipendenti: se una delle due
    # non è calcolabile (es. piatto o size mancanti) l'altra resta comunque utile,
    # quindi si degrada a None invece di far fallire l'intera richiesta con un 422.
    spr = None
    try:
        spr = calculate_spr(request.effective_stack, request.pot_before_call)
    except InvalidMetricsInputError:
        pass

    mdf = None
    try:
        mdf = calculate_mdf(request.pot_before_call, request.amount_to_call)
    except InvalidMetricsInputError:
        pass

    return TableMetricsResponse(spr=spr, mdf=mdf)
