# Guida all'avvio

Comandi per eseguire Texas Engine in locale: in fase di sviluppo/test da PC, e per l'uso reale dal telefono al tavolo (stessa rete wifi/hotspot).

## Requisiti

- Python 3.11+
- [Poetry](https://python-poetry.org/) installato

## 1. Setup iniziale (una tantum)

### Installare Poetry

```powershell
python -m pip install --user poetry
```

**Nota Windows — "poetry non riconosciuto" dopo l'installazione**: `pip install --user` installa `poetry.exe` in una cartella (tipicamente `%APPDATA%\Python\Python3XX\Scripts`) che di norma **non è già nel PATH**. Se dopo l'installazione il comando `poetry` non viene riconosciuto:

1. Aggiungi la cartella al PATH utente (una tantum):
   ```powershell
   $scriptsDir = "$env:APPDATA\Python\Python312\Scripts"  # adatta la versione di Python se diversa
   $currentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
   [Environment]::SetEnvironmentVariable("PATH", "$currentUserPath;$scriptsDir", "User")
   ```
2. **Chiudi e riapri il terminale** (o riavvia VS Code): Windows scrive il PATH nel registro, ma i terminali già aperti non lo rileggono finché non vengono riavviati.
3. Verifica con `poetry --version`.

Se preferisci non toccare il PATH, puoi sempre invocare Poetry con il percorso completo: `& "$env:APPDATA\Python\Python312\Scripts\poetry.exe" <comando>`.

### Installare le dipendenze del progetto

```bash
cd texas_engine
poetry install
```

## 2. Eseguire i test

```bash
poetry run pytest
```

Da fare dopo ogni modifica, prima di considerare uno step concluso.

## 3. Avvio per sviluppo/test da PC

```bash
poetry run uvicorn api.main:app --reload
```

Apri il browser su **http://127.0.0.1:8000**. Il flag `--reload` ricarica il server ad ogni modifica del codice: comodo in sviluppo, da non usare per l'uso reale al tavolo.

## 4. Avvio per l'uso da smartphone (stessa rete wifi/hotspot)

Il PC e il telefono devono essere sulla **stessa rete** (wifi di casa, oppure hotspot del telefono con il PC collegato ad esso).

### 4.1 Avvia il server esponendolo sulla rete locale

```bash
poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` è l'unica differenza rispetto al comando di sviluppo: fa sì che il server accetti connessioni da altri dispositivi della rete, non solo dal PC stesso.

### 4.2 Trova l'indirizzo IP del PC sulla rete locale

**Linux / macOS:**
```bash
hostname -I        # Linux
ifconfig | grep "inet "   # macOS (o Linux se hostname -I non è disponibile)
```

**Windows (PowerShell o cmd):**
```powershell
ipconfig
```
Cerca l'indirizzo alla voce "IPv4 Address" dell'adattatore wifi attivo (tipicamente `192.168.x.x`).

### 4.3 Apri l'app dal telefono

Con il telefono connesso alla stessa rete, apri dal browser mobile:

```
http://<IP_DEL_PC>:8000
```

Esempio: `http://192.168.1.42:8000`

### 4.4 (Opzionale ma consigliato) Installa come app

Dal browser mobile, usa "Aggiungi a schermata Home" (Chrome Android) o "Aggiungi a Home" (Safari iOS): l'app si apre a schermo intero come un'app nativa, senza barra degli indirizzi.

### Problemi comuni

- **Il telefono non raggiunge il PC**: verifica che siano sulla stessa rete (non wifi di casa + dati mobili del telefono). Con hotspot dal telefono, il PC deve essere il dispositivo connesso all'hotspot, non il contrario.
- **Firewall di Windows**: alla prima esecuzione con `--host 0.0.0.0` potrebbe chiedere di consentire l'accesso alla rete per Python — accetta per reti private.
- **Porta già in uso**: cambia porta con `--port 8001` (o altra libera) sia nel comando sia nell'URL da telefono.

## 5. Uso fuori casa (deploy su Render)

Per l'accesso da fuori dalla rete locale, il repo include `render.yaml` per il deploy gratuito su Render. Dettagli e limitazioni (cold start del piano free) nel `README.md`.
