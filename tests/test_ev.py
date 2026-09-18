import pytest

from engine.ev import InvalidEvInputError, calculate_call_ev


def test_ev_positive_when_equity_above_required():
    # Pot 100, call 50 -> pot odds richiede 33.3%; con equity 50% l'EV è positivo
    ev = calculate_call_ev(hero_equity=0.5, amount_to_call=50, pot_before_call=100)
    assert ev == pytest.approx(25.0)


def test_ev_zero_at_breakeven_equity():
    # Con pot 100 e call 50, l'equity di breakeven è esattamente 1/3 (== required_equity di pot_odds)
    ev = calculate_call_ev(hero_equity=1 / 3, amount_to_call=50, pot_before_call=100)
    assert ev == pytest.approx(0.0, abs=1e-9)


def test_ev_negative_when_equity_below_required():
    ev = calculate_call_ev(hero_equity=0.1, amount_to_call=50, pot_before_call=100)
    assert ev < 0


def test_ev_with_zero_equity_equals_minus_call():
    ev = calculate_call_ev(hero_equity=0.0, amount_to_call=50, pot_before_call=100)
    assert ev == pytest.approx(-50.0)


def test_ev_with_certain_win_equals_pot_before_call():
    ev = calculate_call_ev(hero_equity=1.0, amount_to_call=50, pot_before_call=100)
    assert ev == pytest.approx(100.0)


def test_ev_zero_call_equals_equity_share_of_pot():
    # Con call gratuito (check) l'EV è semplicemente la propria quota del piatto esistente
    ev = calculate_call_ev(hero_equity=0.2, amount_to_call=0, pot_before_call=100)
    assert ev == pytest.approx(20.0)


def test_ev_rejects_equity_out_of_range():
    with pytest.raises(InvalidEvInputError):
        calculate_call_ev(hero_equity=1.5, amount_to_call=50, pot_before_call=100)
    with pytest.raises(InvalidEvInputError):
        calculate_call_ev(hero_equity=-0.1, amount_to_call=50, pot_before_call=100)


def test_ev_rejects_negative_amounts():
    with pytest.raises(InvalidEvInputError):
        calculate_call_ev(hero_equity=0.5, amount_to_call=-10, pot_before_call=100)
    with pytest.raises(InvalidEvInputError):
        calculate_call_ev(hero_equity=0.5, amount_to_call=10, pot_before_call=-100)
