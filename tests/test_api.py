import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_equity_endpoint_river_direct_comparison():
    payload = {
        "hero_cards": ["Ah", "Kh"],
        "board": ["Jh", "9h", "2c", "Td", "3h"],
        "villain_cards": [["Qc", "Qd"]],
    }
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["hero_equity"] == 1.0
    assert body["method"] == "direct_comparison"


def test_equity_endpoint_preflop_monte_carlo():
    payload = {
        "hero_cards": ["Ah", "As"],
        "board": [],
        "villain_cards": [["Kh", "Ks"]],
        "iterations": 5000,
    }
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "monte_carlo"
    assert 0.75 < body["hero_equity"] < 0.90


def test_equity_endpoint_rejects_invalid_card():
    payload = {"hero_cards": ["Ah", "Xx"], "board": []}
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 422


def test_equity_endpoint_villain_range():
    payload = {
        "hero_cards": ["Ah", "As"],
        "board": [],
        "villain_ranges": [["KK", "QQ", "AKs"]],
        "iterations": 5000,
    }
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "monte_carlo"
    assert 0.75 < body["hero_equity"] < 0.90


def test_equity_endpoint_rejects_invalid_range_label():
    payload = {"hero_cards": ["Ah", "As"], "board": [], "villain_ranges": [["77s"]]}
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 422


def test_equity_endpoint_rejects_empty_range():
    payload = {"hero_cards": ["Ah", "As"], "board": [], "villain_ranges": [[]]}
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 422


def test_equity_endpoint_rejects_invalid_board_length():
    payload = {"hero_cards": ["Ah", "Kh"], "board": ["2c", "3d"]}
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 422


def test_equity_endpoint_rejects_duplicate_cards():
    payload = {
        "hero_cards": ["Ah", "Kh"],
        "board": [],
        "villain_cards": [["Ah", "Qd"]],
    }
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 422


def test_pot_odds_endpoint():
    response = client.post("/api/pot-odds", json={"amount_to_call": 50, "pot_before_call": 100})
    assert response.status_code == 200
    body = response.json()
    assert body["required_equity"] == pytest.approx(1 / 3)
    assert body["required_equity_percentage"] == pytest.approx(100 / 3)


def test_pot_odds_endpoint_rejects_negative():
    response = client.post("/api/pot-odds", json={"amount_to_call": -1, "pot_before_call": 100})
    assert response.status_code == 422


def test_ev_endpoint_profitable():
    response = client.post("/api/ev", json={"hero_equity": 0.5, "amount_to_call": 50, "pot_before_call": 100})
    assert response.status_code == 200
    body = response.json()
    assert body["ev"] == pytest.approx(25.0)
    assert body["profitable"] is True


def test_ev_endpoint_not_profitable():
    response = client.post("/api/ev", json={"hero_equity": 0.1, "amount_to_call": 50, "pot_before_call": 100})
    assert response.status_code == 200
    body = response.json()
    assert body["ev"] < 0
    assert body["profitable"] is False


def test_ev_endpoint_without_equity_bounds_returns_no_ev_bounds():
    """Con l'enumerazione esatta l'equity non ha intervallo: non va inventato."""
    response = client.post("/api/ev", json={"hero_equity": 0.5, "amount_to_call": 50, "pot_before_call": 100})
    body = response.json()
    assert body["ev_low"] is None
    assert body["ev_high"] is None


def test_ev_endpoint_propagates_equity_confidence_interval_onto_ev():
    """L'incertezza dell'equity stimata deve arrivare fino all'EV, con la stessa formula."""
    payload = {
        "hero_equity": 0.34,
        "hero_equity_low": 0.32,
        "hero_equity_high": 0.36,
        "amount_to_call": 50,
        "pot_before_call": 100,
    }
    response = client.post("/api/ev", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["ev_low"] == pytest.approx(0.32 * 150 - 50)
    assert body["ev_high"] == pytest.approx(0.36 * 150 - 50)
    # Il caso interessante: l'EV puntuale è positivo ma l'intervallo attraversa lo
    # zero, quindi il segno non è stabilito dal campionamento.
    assert body["ev"] > 0
    assert body["ev_low"] < 0 < body["ev_high"]


def test_shove_ev_endpoint_propagates_equity_confidence_interval():
    payload = {
        "hero_equity_if_called": 0.4,
        "hero_equity_low": 0.38,
        "hero_equity_high": 0.42,
        "fold_probability": 0.3,
        "pot_before_shove": 20,
        "shove_amount": 50,
    }
    response = client.post("/api/shove-ev", json=payload)
    assert response.status_code == 200
    body = response.json()

    def expected(equity: float) -> float:
        return 0.3 * 20.0 + 0.7 * (equity * (20 + 2 * 50) - 50)

    assert body["ev_low"] == pytest.approx(expected(0.38))
    assert body["ev_high"] == pytest.approx(expected(0.42))
    assert body["ev_low"] < body["ev"] < body["ev_high"]


def test_ev_endpoint_rejects_equity_out_of_range():
    response = client.post("/api/ev", json={"hero_equity": 1.2, "amount_to_call": 50, "pot_before_call": 100})
    assert response.status_code == 422


def test_shove_ev_endpoint():
    payload = {
        "hero_equity_if_called": 0.4,
        "fold_probability": 0.3,
        "pot_before_shove": 20,
        "shove_amount": 50,
    }
    response = client.post("/api/shove-ev", json=payload)
    assert response.status_code == 200
    body = response.json()
    ev_if_fold = 20.0
    ev_if_called = 0.4 * (20 + 2 * 50) - 50
    expected = 0.3 * ev_if_fold + 0.7 * ev_if_called
    assert body["ev"] == pytest.approx(expected)
    assert body["profitable"] == (expected > 0)


def test_ev_endpoint_with_implied_future_bet():
    response = client.post(
        "/api/ev",
        json={"hero_equity": 0.4, "amount_to_call": 50, "pot_before_call": 100, "implied_future_bet": 30},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ev"] == pytest.approx(0.4 * (100 + 50 + 30) - 50)


def test_equity_endpoint_reports_confidence_interval_for_monte_carlo():
    payload = {
        "hero_cards": ["Ah", "As"],
        "board": [],
        "villain_cards": [["Kh", "Ks"]],
        "iterations": 5000,
    }
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["standard_error"] is not None
    assert body["ci_low"] < body["hero_equity"] < body["ci_high"]


def test_equity_endpoint_no_confidence_interval_for_direct_comparison():
    payload = {
        "hero_cards": ["Ah", "Kh"],
        "board": ["Jh", "9h", "2c", "Td", "3h"],
        "villain_cards": [["Qc", "Qd"]],
    }
    response = client.post("/api/equity", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["standard_error"] is None
    assert body["ci_low"] is None
    assert body["ci_high"] is None


def test_table_metrics_endpoint():
    response = client.post(
        "/api/table-metrics",
        json={"effective_stack": 200, "pot_before_call": 100, "amount_to_call": 50},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["spr"] == pytest.approx(2.0)
    # Piatto 100 comprensivo della puntata da 50 -> MDF = (100-50)/100
    assert body["mdf"] == pytest.approx(0.5)
    assert body["max_implied_bet"] == pytest.approx(150.0)


def test_table_metrics_endpoint_degrades_gracefully_when_pot_is_zero():
    response = client.post(
        "/api/table-metrics",
        json={"effective_stack": 200, "pot_before_call": 0, "amount_to_call": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["spr"] is None
    assert body["mdf"] is None
    assert body["max_implied_bet"] == pytest.approx(200.0)


def test_range_combo_count_endpoint():
    response = client.post(
        "/api/range-combo-count",
        json={"labels": ["AA", "AKs"], "known_cards": []},
    )
    assert response.status_code == 200
    assert response.json()["combo_count"] == 10


def test_range_combo_count_endpoint_accounts_for_known_cards():
    response = client.post(
        "/api/range-combo-count",
        json={"labels": ["AKs"], "known_cards": ["Ah", "Ks"]},
    )
    assert response.status_code == 200
    assert response.json()["combo_count"] == 2


def test_range_combo_count_endpoint_rejects_invalid_label():
    response = client.post(
        "/api/range-combo-count",
        json={"labels": ["77s"], "known_cards": []},
    )
    assert response.status_code == 422


def test_shove_ev_endpoint_rejects_invalid_fold_probability():
    payload = {
        "hero_equity_if_called": 0.4,
        "fold_probability": 1.2,
        "pot_before_shove": 20,
        "shove_amount": 50,
    }
    response = client.post("/api/shove-ev", json=payload)
    assert response.status_code == 422
