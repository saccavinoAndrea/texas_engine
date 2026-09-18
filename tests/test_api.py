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
