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

Per i comandi di avvio dettagliati vedi [`GUIDA_AVVIO.md`](GUIDA_AVVIO.md); per usare l'app dal telefono, con o senza il PC acceso, vedi [`GUIDA_SMARTPHONE.md`](GUIDA_SMARTPHONE.md).

## Deploy (Render, piano free)

Il repo include `render.yaml`: basta collegare il repo su Render e verrà creato un web service Python che builda con Poetry e serve `api.main:app` via uvicorn.

**Nota sul piano free**: il servizio va in sleep dopo ~15 minuti di inattività; la prima richiesta dopo lo sleep può impiegare 30-50 secondi a rispondere. Prima di sedersi al tavolo, apri l'app qualche minuto prima (o chiama `GET /api/health`) per "svegliarla".

## API

- `POST /api/equity` — equity vs mani note, range (definiti dall'utente, es. "AA,KK,AKs") e/o ignote/random (fino a 8 avversari), split pot gestito proporzionalmente. Il metodo si sceglie da sé in base a quante combinazioni restano davvero da scoprire:
  - tutte le mani note e board completo → confronto diretto
  - combinazioni residue sotto la soglia `EXACT_ENUMERATION_MAX_COMBOS` (con al massimo 1 avversario a mano ignota) → enumerazione esatta: rientrano turn e river, anche con avversari a range, e il flop quando le mani avversarie sono note
  - tutto il resto — preflop, 2+ avversari ignoti, range su un board ancora tutto da scoprire → Monte Carlo (iterazioni configurabili), con errore standard e intervallo di confidenza al 95% nella risposta
- `POST /api/pot-odds` — equity minima richiesta per un call profittevole
- `POST /api/ev` — EV di una chiamata data l'equity, il piatto e l'importo da chiamare; `implied_future_bet` opzionale per le implied odds stimate dall'utente
- `POST /api/shove-ev` — EV di un all-in con fold equity (percentuale di fold stimata dall'utente, non calcolata dal motore)
- `POST /api/table-metrics` — SPR, MDF e tetto teorico per le implied odds (quanto resta nello stack dopo la chiamata); i valori non calcolabili tornano `null` invece di far fallire la richiesta
- `POST /api/range-combo-count` — quante combinazioni concrete restano in un range dopo i blocker delle carte note
- `GET /api/health` — health check / warm-up

## Limitazioni note (MVP)

- I range avversario sono definiti manualmente dall'utente (classi di mano tipo "AKs", "77", "QJo"); non c'è alcun suggerimento o calcolo automatico di range ottimali (nessun solver GTO)
- Nessuna stima automatica di fold equity: va inserita come lettura propria dell'utente
- Nessuno storico delle mani: lo stato vive solo nel browser durante la sessione
