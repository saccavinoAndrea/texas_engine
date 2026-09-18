"""Fixture per i test end-to-end: avvia un vero server uvicorn e lo serve a un
vero browser tramite Playwright.

Separati da tests/ apposta: la suite normale (`poetry run pytest`) resta la
verifica veloce di motore e API, senza bisogno di un browser installato. Questi
si lanciano esplicitamente con `poetry run pytest tests_e2e`.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import urllib.request
import urllib.error

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_healthy(base_url: str, process: subprocess.Popen, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"il server è terminato da solo (exit code {process.returncode}) prima di rispondere")
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(0.2)
    raise TimeoutError(f"il server non ha risposto a /api/health entro {timeout}s")


@pytest.fixture(scope="session")
def live_server(tmp_path_factory) -> Iterator[str]:
    """Avvia `uvicorn api.main:app` su una porta libera dedicata ai test, mai
    quella di sviluppo (8000): non deve mai poter interferire con un server che
    l'utente ha avviato lui stesso."""
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    # Il log va su un file vero, mai su una PIPE che nessuno legge: uvicorn scrive
    # una riga per ogni richiesta (health check compreso), il buffer della pipe si
    # riempie dopo poche decine di richieste e il processo si blocca in scrittura,
    # bloccando con sé l'intero server — visto qui: i primi test passavano, poi
    # ogni pagina successiva restava appesa fino al timeout di Playwright.
    log_path = tmp_path_factory.mktemp("uvicorn") / "server.log"
    log_file = log_path.open("w", encoding="utf-8")

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--port", str(port)],
        cwd=PROJECT_ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    try:
        try:
            _wait_until_healthy(base_url, process)
        except (RuntimeError, TimeoutError) as exc:
            log_file.flush()
            raise RuntimeError(f"{exc}\n--- log del server ---\n{log_path.read_text(encoding='utf-8')}") from exc
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        log_file.close()
        # Non deve restare nessun processo appeso dopo la sessione di test.
        assert process.poll() is not None, "il server di test non si è chiuso correttamente"


@pytest.fixture
def app_page(page, live_server):
    """Una pagina già caricata sull'app, pronta per interagire."""
    page.goto(live_server)
    page.wait_for_selector("#calcolaBtn")
    return page
