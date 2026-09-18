# Texas Engine

Motore di supporto live per Texas Hold'em cash game: equity e pot odds, usabile da smartphone al tavolo. Nessuna persistenza delle mani, nessun solver GTO — solo calcolo su richiesta per la mano in corso.

## Struttura del progetto

```
engine/     logica pura (carte, evaluator, equity, pot odds, ev, range), zero dipendenze da FastAPI
api/        FastAPI: schemas Pydantic, router, static files della PWA
frontend/   PWA (Bootstrap5 vendorizzato localmente, nessuna dipendenza da CDN esterni)
tests/      pytest su engine/ e sugli endpoint API
```

## Sviluppo locale

```bash
poetry install
poetry run pytest
poetry run uvicorn api.main:app --reload
```

L'app (API + frontend) sarà su `http://127.0.0.1:8000`.

Per i comandi di avvio dettagliati — incluso l'accesso da smartphone sulla stessa rete wifi/hotspot — vedi [`GUIDA_AVVIO.md`](GUIDA_AVVIO.md).

## Deploy (Render, piano free)

Il repo include `render.yaml`: basta collegare il repo su Render e verrà creato un web service Python che builda con Poetry e serve `api.main:app` via uvicorn.

**Nota sul piano free**: il servizio va in sleep dopo ~15 minuti di inattività; la prima richiesta dopo lo sleep può impiegare 30-50 secondi a rispondere. Prima di sedersi al tavolo, apri l'app qualche minuto prima (o chiama `GET /api/health`) per "svegliarla".

## API

- `POST /api/equity` — equity vs mani note, range (definiti dall'utente, es. "AA,KK,AKs") e/o ignote/random (fino a 8 avversari), split pot gestito proporzionalmente
  - preflop/flop → Monte Carlo (iterazioni configurabili)
  - turn/river con al massimo 1 avversario ignoto e nessun range → enumerazione esatta
  - turn/river con 2+ avversari ignoti, o con un range su qualunque avversario → Monte Carlo (l'enumerazione esatta esploderebbe o richiederebbe una gestione combinatoria dedicata)
  - river con tutte le mani note → confronto diretto
- `POST /api/pot-odds` — equity minima richiesta per un call profittevole
- `POST /api/ev` — EV di una chiamata data l'equity, il piatto e l'importo da chiamare
- `POST /api/shove-ev` — EV di un all-in con fold equity (percentuale di fold stimata dall'utente, non calcolata dal motore)
- `GET /api/health` — health check / warm-up

## Limitazioni note (MVP)

- I range avversario sono definiti manualmente dall'utente (classi di mano tipo "AKs", "77", "QJo"); non c'è alcun suggerimento o calcolo automatico di range ottimali (nessun solver GTO)
- Nessuna stima automatica di fold equity: va inserita come lettura propria dell'utente
- Nessuno storico delle mani: lo stato vive solo nel browser durante la sessione
