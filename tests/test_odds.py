import pytest

from engine.odds import InvalidPotOddsInputError, pot_odds


def test_pot_odds_basic():
    # Pot 100, call 50 -> required equity = 50 / (100+50) = 33.3%
    assert pot_odds(amount_to_call=50, pot_before_call=100) == pytest.approx(1 / 3)


def test_pot_odds_zero_call_is_free():
    assert pot_odds(amount_to_call=0, pot_before_call=100) == 0.0


def test_pot_odds_call_equal_to_pot():
    assert pot_odds(amount_to_call=100, pot_before_call=100) == pytest.approx(0.5)


def test_pot_odds_rejects_negative_amounts():
    with pytest.raises(InvalidPotOddsInputError):
        pot_odds(amount_to_call=-10, pot_before_call=100)

    with pytest.raises(InvalidPotOddsInputError):
        pot_odds(amount_to_call=10, pot_before_call=-5)
