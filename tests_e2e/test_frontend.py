"""Test end-to-end sul frontend reale, con un vero browser (Playwright) contro un
vero server uvicorn: la prima verifica visiva/interattiva della SPA in tutto il
progetto. Finora il frontend era stato solo letto e controllato via HTTP a basso
livello — qui invece si clicca, si digita, si legge il DOM come farebbe l'utente.
"""

from __future__ import annotations

import re

from playwright.sync_api import expect

SUIT_SYMBOL = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}


def pick_card(page, slot: str, code: str) -> None:
    """Apre il picker per uno slot e sceglie la carta data (es. 'Ah')."""
    page.click(f'[data-slot="{slot}"]')
    rank, suit = code[0], code[1]
    page.click(f'#pickerGrid img[alt="{rank}{SUIT_SYMBOL[suit]}"]')


def set_table_size(page, opponents_plus_hero: int) -> None:
    page.select_option("#tableSize", str(opponents_plus_hero))


def fill(page, field_id: str, value: str) -> None:
    page.fill(f"#{field_id}", value)


# --------------------------------------------------------------------------
# Caricamento e stato iniziale
# --------------------------------------------------------------------------


def test_app_loads_with_results_hidden(app_page):
    assert app_page.title() == "Texas Engine"
    assert app_page.is_hidden("#results")
    assert app_page.is_hidden("#errorBox")


def test_calcola_without_hero_cards_shows_error(app_page):
    app_page.click("#calcolaBtn")
    error_box = app_page.locator("#errorBox")
    expect(error_box).to_contain_text("Seleziona entrambe le tue carte")
    assert app_page.is_hidden("#results")


def test_picker_disables_a_card_already_used_by_hero1(app_page):
    """La stessa carta non deve poter finire in due slot: il picker la disabilita."""
    pick_card(app_page, "hero1", "Ah")
    app_page.click('[data-slot="hero2"]')
    ah_button = app_page.locator('#pickerGrid img[alt="A♥"]').locator("xpath=..")
    assert ah_button.is_disabled()


# --------------------------------------------------------------------------
# Percorso completo: preflop, chiamata profittevole
# --------------------------------------------------------------------------


def test_full_happy_path_shows_positive_verdict(app_page):
    pick_card(app_page, "hero1", "Ah")
    pick_card(app_page, "hero2", "As")
    fill(app_page, "potBeforeCall", "100")
    fill(app_page, "amountToCall", "10")

    app_page.click("#calcolaBtn")
    verdict = app_page.locator("#verdict")
    expect(verdict).to_contain_text("EV positivo")
    expect(verdict).to_have_class(re.compile("alert-success"))

    hero_equity_text = app_page.locator("#heroEquity").inner_text()
    assert re.match(r"^\d+\.\d%$", hero_equity_text)
    # Pocket aces preflop: equity nettamente sopra il 50% anche multiway a 1 avversario.
    assert float(hero_equity_text.rstrip("%")) > 70.0

    meta_text = app_page.locator("#meta").inner_text()
    assert "Monte Carlo" in meta_text or "scenari" in meta_text


def test_river_with_known_hands_uses_direct_comparison(app_page):
    """Board completo e mani entrambe note: un solo caso possibile, nessun campionamento."""
    pick_card(app_page, "hero1", "Ah")
    pick_card(app_page, "hero2", "Ad")
    pick_card(app_page, "flop1", "2c")
    pick_card(app_page, "flop2", "7d")
    pick_card(app_page, "flop3", "9h")
    pick_card(app_page, "turn", "Jc")
    pick_card(app_page, "river", "3s")

    set_table_size(app_page, 2)
    app_page.click('.villain-mode-btn[data-villain="1"][data-mode="known"]')
    pick_card(app_page, "villain1_1", "Kh")
    pick_card(app_page, "villain1_2", "Kd")

    fill(app_page, "potBeforeCall", "50")
    fill(app_page, "amountToCall", "10")
    app_page.click("#calcolaBtn")

    meta = app_page.locator("#meta")
    expect(meta).to_contain_text("Confronto diretto")
    assert app_page.locator("#heroEquity").inner_text() == "100.0%"
    # Metodo esatto: nessun intervallo di confidenza da mostrare.
    assert app_page.is_hidden("#equityConfidence")


# --------------------------------------------------------------------------
# Verdetto neutro senza nulla da chiamare (logica introdotta in questo giro)
# --------------------------------------------------------------------------


def test_no_amount_to_call_gives_neutral_verdict(app_page):
    pick_card(app_page, "hero1", "Ah")
    pick_card(app_page, "hero2", "As")
    fill(app_page, "potBeforeCall", "20")
    fill(app_page, "amountToCall", "0")

    app_page.click("#calcolaBtn")
    verdict = app_page.locator("#verdict")
    expect(verdict).to_have_text("Nessuna chiamata da valutare")
    expect(verdict).to_have_class(re.compile("alert-secondary"))

    note = app_page.locator("#verdictNote")
    expect(note).to_contain_text("non c'è una chiamata da giudicare")


# --------------------------------------------------------------------------
# Implied odds: la seconda soglia deve comparire quando davvero cambia qualcosa
# --------------------------------------------------------------------------


def test_implied_odds_show_the_adjusted_threshold(app_page):
    pick_card(app_page, "hero1", "7h")
    pick_card(app_page, "hero2", "6h")
    fill(app_page, "potBeforeCall", "100")
    fill(app_page, "amountToCall", "50")
    fill(app_page, "impliedFutureBet", "80")

    app_page.click("#calcolaBtn")
    implied_hint = app_page.locator("#requiredEquityImplied")
    expect(implied_hint).to_be_visible()
    expect(implied_hint).to_contain_text("con implied:")

    # Senza implied odds la soglia aggiuntiva non deve comparire. #results resta
    # visibile dal calcolo precedente, quindi il segnale di "fatto" da attendere
    # è che il pulsante torni cliccabile (la richiesta è terminata), non che
    # #results ricompaia: sarebbe già vero prima che la seconda risposta arrivi.
    fill(app_page, "impliedFutureBet", "0")
    app_page.click("#calcolaBtn")
    expect(app_page.locator("#calcolaBtn")).to_have_text("Calcola")
    expect(implied_hint).to_be_hidden()


# --------------------------------------------------------------------------
# Range avversario: flusso completo con vera chiamata API al conteggio combo
# --------------------------------------------------------------------------


def test_villain_range_flow_updates_combo_count_via_real_api_call(app_page):
    pick_card(app_page, "hero1", "Ah")
    pick_card(app_page, "hero2", "Kd")
    set_table_size(app_page, 2)

    app_page.click('.villain-mode-btn[data-villain="1"][data-mode="range"]')
    app_page.click('.villain-range-btn[data-villain="1"]')
    app_page.wait_for_selector("#rangeModal.show")

    app_page.click('.range-cell[data-label="AA"]')
    app_page.click('.range-cell[data-label="AKs"]')

    # AA ha 6 combo (ogni coppia di semi tra i 4 assi): Ah ne blocca 3 (quelle in
    # cui compare), ne restano 3. AKs ha 4 combo, una bloccata dall'Ah e una dal
    # Kd di hero: restano 2. Totale 5. Il conteggio arriva da una vera chiamata
    # asincrona a /api/range-combo-count, quindi l'asserzione deve attendere
    # (expect ritenta), non leggere uno snapshot.
    summary = app_page.locator("#rangeSummary")
    expect(summary).to_contain_text("2 classi selezionate · 5 combo utilizzabili")

    app_page.click('#rangeModal .btn-success')  # "Fatto"
    expect(app_page.locator("#rangeModal")).to_be_hidden()

    villain_btn = app_page.locator('.villain-range-btn[data-villain="1"]')
    expect(villain_btn).to_contain_text("2 classi")


# --------------------------------------------------------------------------
# Avvisi di coerenza multiway
# --------------------------------------------------------------------------


def test_villain_consistency_warning_appears_when_partially_customized(app_page):
    set_table_size(app_page, 3)  # 2 avversari
    assert app_page.is_hidden("#villainConsistencyWarning")

    app_page.click('.villain-mode-btn[data-villain="1"][data-mode="known"]')
    warning = app_page.locator("#villainConsistencyWarning")
    assert warning.is_visible()
    assert "1 avversari su 2" in warning.inner_text()

    app_page.click('.villain-mode-btn[data-villain="2"][data-mode="known"]')
    assert app_page.is_hidden("#villainConsistencyWarning")


# --------------------------------------------------------------------------
# Shove EV
# --------------------------------------------------------------------------


def test_shove_validation_blocks_amount_not_exceeding_call(app_page):
    pick_card(app_page, "hero1", "Ah")
    pick_card(app_page, "hero2", "As")
    fill(app_page, "potBeforeCall", "20")
    fill(app_page, "amountToCall", "10")

    app_page.check("#enableShove")
    fill(app_page, "shoveAmount", "10")  # uguale alla call: non valido
    fill(app_page, "foldProbability", "40")

    app_page.click("#calcolaBtn")
    expect(app_page.locator("#errorBox")).to_contain_text("deve superare quanto c'è da chiamare")


def test_shove_ev_flow_shows_result_card(app_page):
    pick_card(app_page, "hero1", "Ah")
    pick_card(app_page, "hero2", "As")
    fill(app_page, "potBeforeCall", "20")
    fill(app_page, "amountToCall", "10")

    app_page.check("#enableShove")
    fill(app_page, "shoveAmount", "100")
    fill(app_page, "foldProbability", "40")

    app_page.click("#calcolaBtn")
    expect(app_page.locator("#verdict")).to_contain_text("shove")

    shove_value = app_page.locator("#shoveEvValue").inner_text()
    assert re.match(r"^[+-]\d+\.\d\d$", shove_value)


# --------------------------------------------------------------------------
# Scorciatoie ÷2 / ×2
# --------------------------------------------------------------------------


def test_halve_and_double_shortcuts_on_amount_to_call(app_page):
    fill(app_page, "amountToCall", "20")
    app_page.click("#halveCallBtn")
    assert app_page.input_value("#amountToCall") == "10.00"
    app_page.click("#doubleCallBtn")
    assert app_page.input_value("#amountToCall") == "20.00"


# --------------------------------------------------------------------------
# Storico sessione
# --------------------------------------------------------------------------


def test_history_records_a_calculation_and_can_be_cleared(app_page):
    pick_card(app_page, "hero1", "Ah")
    pick_card(app_page, "hero2", "As")
    fill(app_page, "potBeforeCall", "20")
    fill(app_page, "amountToCall", "5")
    app_page.click("#calcolaBtn")

    app_page.click('button:has-text("Storico sessione")')
    history_list = app_page.locator("#historyList")
    expect(history_list).to_contain_text("avversari")
    assert app_page.is_hidden("#historyEmpty")

    app_page.click("#clearHistoryBtn")
    assert app_page.is_visible("#historyEmpty")
    assert history_list.inner_text().strip() == ""


# --------------------------------------------------------------------------
# Popover informativi e guida rapida
# --------------------------------------------------------------------------


def test_info_popover_shows_expected_content(app_page):
    app_page.click('.field-label:has-text("Da chiamare") button.info-btn')
    popover = app_page.locator(".popover")
    expect(popover).to_be_visible()
    expect(popover).to_contain_text("pareggiare la puntata avversaria")


def test_guide_modal_opens_and_accordion_expands(app_page):
    app_page.click('button:has-text("Guida")')
    expect(app_page.locator("#guideModal")).to_be_visible()
    # guide1 è aperta di default (classe "show" nell'HTML): il suo contenuto,
    # non il titolo del bottone (che vive nell'header, fuori dal pannello).
    expect(app_page.locator("#guide1")).to_contain_text("dealer")

    app_page.click('button:has-text("Equity, pot odds ed EV")')
    guide4 = app_page.locator("#guide4")
    expect(guide4).to_be_visible()
    expect(guide4).to_contain_text("EV al limite")
