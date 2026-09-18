import pytest

from engine.ev import calculate_call_ev
from engine.odds import InvalidPotOddsInputError, pot_odds


def test_pot_odds_basic():
    # Pot 100, call 50 -> required equity = 50 / (100+50) = 33.3%
    assert pot_odds(amount_to_call=50, pot_before_call=100) == pytest.approx(1 / 3)


def test_pot_odds_zero_call_is_free():
    assert pot_odds(amount_to_call=0, pot_before_call=100) == 0.0


def test_pot_odds_call_equal_to_pot():
    assert pot_odds(amount_to_call=100, pot_before_call=100) == pytest.approx(0.5)


def test_pot_odds_with_implied_lower_the_break_even_threshold():
    """Le implied odds allargano il piatto che punti a vincere, quindi ti serve
    meno equity per pareggiare: 50 / (100 + 50 + 80) invece di 50 / 150."""
    assert pot_odds(amount_to_call=50, pot_before_call=100, implied_future_bet=80) == pytest.approx(50 / 230)


def test_pot_odds_with_implied_matches_the_break_even_point_of_the_ev():
    """Controllo incrociato con l'altra funzione: alla soglia restituita l'EV
    della chiamata deve valere esattamente zero, altrimenti i due numeri
    mostrati insieme dall'app si contraddicono."""
    pot, call, implied = 120.0, 40.0, 60.0

    soglia = pot_odds(amount_to_call=call, pot_before_call=pot, implied_future_bet=implied)
    ev_alla_soglia = calculate_call_ev(soglia, amount_to_call=call, pot_before_call=pot, implied_future_bet=implied)

    assert ev_alla_soglia == pytest.approx(0.0, abs=1e-9)
    # e appena sopra la soglia la chiamata è già profittevole
    assert calculate_call_ev(soglia + 0.01, call, pot, implied) > 0


def test_pot_odds_without_implied_is_unchanged():
    assert pot_odds(amount_to_call=50, pot_before_call=100, implied_future_bet=0) == pytest.approx(1 / 3)


def test_pot_odds_rejects_negative_amounts():
    with pytest.raises(InvalidPotOddsInputError):
        pot_odds(amount_to_call=-10, pot_before_call=100)

    with pytest.raises(InvalidPotOddsInputError):
        pot_odds(amount_to_call=10, pot_before_call=-5)

    with pytest.raises(InvalidPotOddsInputError):
        pot_odds(amount_to_call=10, pot_before_call=100, implied_future_bet=-1)
