import pytest

from engine.metrics import InvalidMetricsInputError, calculate_mdf, calculate_spr


def test_spr_basic():
    assert calculate_spr(effective_stack=200, pot=100) == pytest.approx(2.0)


def test_spr_rejects_zero_pot():
    with pytest.raises(InvalidMetricsInputError):
        calculate_spr(effective_stack=200, pot=0)


def test_spr_rejects_negative_amounts():
    with pytest.raises(InvalidMetricsInputError):
        calculate_spr(effective_stack=-1, pot=100)
    with pytest.raises(InvalidMetricsInputError):
        calculate_spr(effective_stack=200, pot=-1)


def test_mdf_basic():
    # Piatto 100, puntata 50 -> MDF = 100 / (100+50) = 2/3
    assert calculate_mdf(pot_before_bet=100, bet_size=50) == pytest.approx(2 / 3)


def test_mdf_pot_sized_bet_is_one_half():
    assert calculate_mdf(pot_before_bet=100, bet_size=100) == pytest.approx(0.5)


def test_mdf_rejects_zero_bet_size():
    with pytest.raises(InvalidMetricsInputError):
        calculate_mdf(pot_before_bet=100, bet_size=0)


def test_mdf_rejects_negative_amounts():
    with pytest.raises(InvalidMetricsInputError):
        calculate_mdf(pot_before_bet=-1, bet_size=50)
    with pytest.raises(InvalidMetricsInputError):
        calculate_mdf(pot_before_bet=100, bet_size=-1)
