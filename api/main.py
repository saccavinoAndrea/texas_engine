from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routers import equity, ev, metrics, odds, ranges

app = FastAPI(title="Texas Engine API", description="Equity e pot odds per Texas Hold'em cash game")

app.include_router(equity.router)
app.include_router(odds.router)
app.include_router(ev.router)
app.include_router(metrics.router)
app.include_router(ranges.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
