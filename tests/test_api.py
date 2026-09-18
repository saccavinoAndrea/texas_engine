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


def test_shove_ev_endpoint_rejects_invalid_fold_probability():
    payload = {
        "hero_equity_if_called": 0.4,
        "fold_probability": 1.2,
        "pot_before_shove": 20,
        "shove_amount": 50,
    }
    response = client.post("/api/shove-ev", json=payload)
    assert response.status_code == 422
