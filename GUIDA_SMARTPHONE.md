# Guida all'uso da smartphone (Android)

Due modi per usare Texas Engine dal telefono. Servono a cose diverse, quindi conviene sapere prima quale ti serve.

| | **Modalità A — con il PC** | **Modalità B — senza il PC** |
|---|---|---|
| Dove gira il backend | Sul tuo PC | Su un server gratuito (Render) |
| Serve il PC acceso | Sì, sempre | No |
| Dove funziona | Solo sulla stessa rete del PC | Ovunque ci sia internet |
| Velocità | Immediata | Immediata, ma la **prima** richiesta dopo una pausa richiede 30-50 secondi |
| Si installa come vera app | No (vedi sotto il perché) | Sì |
| Quando usarla | Test e prove in casa | Uso reale al tavolo |

In pratica: la **A** per provare l'app mentre la sviluppiamo, la **B** per averla davvero in tasca quando giochi.

---

## Modalità A — telefono con il backend sul tuo PC

Il telefono fa da schermo, i calcoli li fa il PC. Entrambi devono essere sulla **stessa rete**: stesso wifi di casa, oppure PC collegato all'hotspot del telefono (non il contrario).

### Passo 1 — Avvia il server sul PC

Apri PowerShell nella cartella del progetto e lancia:

```bash
poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

L'unica differenza rispetto all'avvio normale è `--host 0.0.0.0`: senza quello il server accetta richieste solo dal PC stesso e il telefono non lo vedrebbe.

Lascia questa finestra aperta: finché resta aperta, il server è attivo.

### Passo 2 — Autorizza il firewall (solo la prima volta)

Windows mostrerà una finestra che chiede se consentire l'accesso alla rete a Python. Seleziona **Reti private** e conferma.

Se per sbaglio hai cliccato "Annulla", il telefono non riuscirà a connettersi. Per rimediare, apri PowerShell **come amministratore** e lancia:

```powershell
netsh advfirewall firewall add rule name="Texas Engine" dir=in action=allow protocol=TCP localport=8000
```

Questo apre la porta 8000 sul PC. Quando hai finito di usare l'app puoi rimuovere la regola con lo stesso comando sostituendo `add` con `delete`.

### Passo 3 — Trova l'indirizzo IP del PC

In PowerShell (una finestra nuova, non quella del server):

```powershell
ipconfig
```

Cerca la sezione dell'adattatore wifi attivo e leggi la voce **IPv4 Address**: sarà qualcosa come `192.168.1.42`.

### Passo 4 — Apri l'app sul telefono

Su Chrome Android, nella barra degli indirizzi scrivi l'IP seguito dalla porta:

```
http://192.168.1.42:8000
```

(sostituendo l'IP con il tuo). Deve comparire l'interfaccia di Texas Engine.

### Passo 5 — Prova che i calcoli funzionino davvero

Non fermarti a vedere la schermata: quella si carica anche senza backend. Fai una prova completa:

1. tocca le due caselle "Le tue carte" e scegli due carte
2. inserisci un piatto (es. 10) e un importo da chiamare (es. 5)
3. premi **Calcola**

Se compaiono equity, EV e verdetto, il collegamento col PC funziona. Se compare "Server non raggiungibile", il telefono non sta parlando col PC: vedi i problemi comuni più sotto.

### Passo 6 — Comodità: scorciatoia sulla schermata Home

Menu di Chrome (tre puntini) → **Aggiungi a schermata Home**. Ottieni un'icona che apre subito l'app.

In questa modalità sarà una semplice scorciatoia, non una vera app installata: Android considera "sicuri" solo gli indirizzi `https://` (e `localhost`), e un indirizzo `http://192.168.x.x` non lo è. Di conseguenza qui non funzionano né l'installazione completa né il funzionamento offline. È un limite del browser, non dell'app, e sparisce nella Modalità B.

### Passo 7 — Quando hai finito, ferma il server

Nella finestra dove gira il server premi **Ctrl+C**.

Attenzione a un dettaglio che confonde: dopo aver fermato il server, se ricarichi l'app sul telefono **potresti continuare a vedere la schermata**. È normale, è il browser che mostra la pagina dalla sua cache. La prova del nove è premere **Calcola**: se il server è spento comparirà "Server non raggiungibile".

Per essere certo che sul PC non sia rimasto nulla acceso:

```powershell
tasklist | findstr python
```

Se non compare niente, non c'è nessun server attivo.

### Problemi comuni

| Sintomo | Causa probabile | Cosa fare |
|---|---|---|
| La pagina non si apre proprio | Telefono e PC su reti diverse | Verifica che il telefono sia sul wifi di casa e non su dati mobili |
| La pagina non si apre proprio | Firewall che blocca | Rifai il Passo 2 |
| "Server non raggiungibile" premendo Calcola | Server spento o finestra chiusa | Rilancia il comando del Passo 1 |
| Funzionava ieri, oggi no | L'IP del PC è cambiato | Rifai il Passo 3 e usa il nuovo IP |
| Si blocca dopo qualche minuto | Il PC è andato in sospensione | Imposta il PC per non sospendersi mentre usi l'app |

---

## Modalità B — telefono senza il PC (deploy gratuito su Render)

Qui il backend gira su un server gratuito raggiungibile da internet: il PC può restare spento, e l'app funziona anche fuori casa, in mobilità.

### Prerequisiti

- Il codice deve essere su GitHub (già lo è)
- Un account gratuito su [render.com](https://render.com) (si registra con GitHub in un minuto)

### Passo 1 — Porta su `main` la versione da pubblicare

Render pubblica quello che trova sul branch principale, quindi assicurati di aver mergiato le modifiche che vuoi usare.

### Passo 2 — Crea il servizio su Render

1. Entra su Render e collega il tuo account GitHub, autorizzando l'accesso al repository `texas_engine`
2. Dalla dashboard scegli **New +** → **Blueprint**
3. Seleziona il repository `texas_engine`

Render legge da solo il file `render.yaml` già presente nel repo, che contiene tutta la configurazione (come installare le dipendenze e come avviare il server). Conferma con **Apply**.

Se l'opzione Blueprint non dovesse comparire, puoi fare la stessa cosa a mano: **New +** → **Web Service** → scegli il repo → runtime Python → build `pip install poetry && poetry config virtualenvs.create false && poetry install --only main` → start `uvicorn api.main:app --host 0.0.0.0 --port $PORT` → piano **Free**.

### Passo 3 — Aspetta la prima pubblicazione

La prima build richiede qualche minuto (installa Python e le dipendenze). Quando finisce, Render mostra lo stato **Live** e un indirizzo pubblico tipo:

```
https://texas-engine-xxxx.onrender.com
```

### Passo 4 — Apri l'app dal telefono

Apri quell'indirizzo con Chrome su Android. Fai la stessa prova del Passo 5 della Modalità A (due carte, piatto, importo, Calcola) per verificare che risponda.

### Passo 5 — Installala come vera app

Menu di Chrome (tre puntini) → **Installa app** (oppure "Aggiungi a schermata Home").

Qui, essendo un indirizzo `https://`, l'installazione è completa: l'app si apre a schermo intero senza barra degli indirizzi e la sua interfaccia resta disponibile anche senza rete. Attenzione però: **i calcoli hanno sempre bisogno della connessione**, perché li esegue il server. Senza rete vedrai l'interfaccia ma premendo Calcola comparirà l'avviso che il server non è raggiungibile.

### Passo 6 — Convivere col piano gratuito

Il piano free di Render **spegne il servizio dopo circa 15 minuti di inattività**. Non lo perdi: si riaccende da solo alla richiesta successiva, ma quella prima richiesta può metterci **30-50 secondi**.

In pratica, prima di sederti al tavolo: apri l'app qualche minuto prima e fai un calcolo qualsiasi. Da quel momento risponde immediatamente finché continui a usarla.

### Da sapere

- **L'indirizzo è pubblico**: non c'è alcuna password, chiunque abbia il link può aprire l'app. Non ci sono tuoi dati dentro (l'app non salva nulla), ma tienilo presente e non diffondere il link.
- **Nessuna mano viene salvata**, nemmeno sul server: vale online esattamente come in locale.
- **Aggiornamenti**: ogni volta che pubblichi modifiche su `main`, Render ricostruisce e aggiorna l'app da solo. Sul telefono basta riaprirla.

---

## In sintesi

Per provare le modifiche mentre lavoriamo insieme: **Modalità A**, più immediata, basta lanciare un comando sul PC.

Per avere l'app davvero utilizzabile al tavolo: **Modalità B**, da configurare una volta sola, poi il PC non serve più.

Le due non si escludono: puoi tenere la B come installazione stabile sul telefono e usare la A quando vuoi provare qualcosa di nuovo prima di pubblicarlo.
