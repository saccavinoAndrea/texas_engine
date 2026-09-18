import pytest

from engine.ev import InvalidEvInputError, calculate_call_ev, calculate_shove_ev


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


def test_ev_implied_future_bet_adds_equity_weighted_value():
    # L'implied bet vale solo nella quota di showdown vinta (equity), non per intero.
    ev_without = calculate_call_ev(hero_equity=0.4, amount_to_call=50, pot_before_call=100)
    ev_with = calculate_call_ev(hero_equity=0.4, amount_to_call=50, pot_before_call=100, implied_future_bet=30)
    assert ev_with - ev_without == pytest.approx(0.4 * 30)


def test_ev_implied_future_bet_defaults_to_zero():
    ev_default = calculate_call_ev(hero_equity=0.4, amount_to_call=50, pot_before_call=100)
    ev_explicit_zero = calculate_call_ev(hero_equity=0.4, amount_to_call=50, pot_before_call=100, implied_future_bet=0)
    assert ev_default == pytest.approx(ev_explicit_zero)


def test_ev_rejects_negative_implied_future_bet():
    with pytest.raises(InvalidEvInputError):
        calculate_call_ev(hero_equity=0.5, amount_to_call=10, pot_before_call=100, implied_future_bet=-1)


def test_shove_ev_always_folds_wins_current_pot():
    ev = calculate_shove_ev(hero_equity_if_called=0.3, fold_probability=1.0, pot_before_shove=20, shove_amount=50)
    assert ev == pytest.approx(20.0)


def test_shove_ev_never_folds_matches_call_ev_with_matched_pot():
    # Con fold_probability=0 lo shove equivale a un call certo, contro un piatto
    # che include già la somma eguagliata dall'avversario.
    hero_equity = 0.4
    pot_before_shove = 20
    shove_amount = 50

    shove = calculate_shove_ev(
        hero_equity_if_called=hero_equity,
        fold_probability=0.0,
        pot_before_shove=pot_before_shove,
        shove_amount=shove_amount,
    )
    equivalent_call = calculate_call_ev(
        hero_equity=hero_equity,
        amount_to_call=shove_amount,
        pot_before_call=pot_before_shove + shove_amount,
    )
    assert shove == pytest.approx(equivalent_call)


def test_shove_ev_interpolates_between_fold_and_call_outcomes():
    ev = calculate_shove_ev(hero_equity_if_called=0.2, fold_probability=0.5, pot_before_shove=10, shove_amount=20)
    ev_if_fold = 10.0
    ev_if_called = 0.2 * (10 + 2 * 20) - 20
    assert ev == pytest.approx(0.5 * ev_if_fold + 0.5 * ev_if_called)


def test_shove_ev_rejects_invalid_probabilities():
    with pytest.raises(InvalidEvInputError):
        calculate_shove_ev(hero_equity_if_called=1.5, fold_probability=0.5, pot_before_shove=10, shove_amount=20)
    with pytest.raises(InvalidEvInputError):
        calculate_shove_ev(hero_equity_if_called=0.5, fold_probability=1.5, pot_before_shove=10, shove_amount=20)


def test_shove_ev_rejects_negative_amounts():
    with pytest.raises(InvalidEvInputError):
        calculate_shove_ev(hero_equity_if_called=0.5, fold_probability=0.5, pot_before_shove=-10, shove_amount=20)
    with pytest.raises(InvalidEvInputError):
        calculate_shove_ev(hero_equity_if_called=0.5, fold_probability=0.5, pot_before_shove=10, shove_amount=-20)


def test_shove_over_a_bet_does_not_count_the_villain_money_twice():
    """Rilancio all-in sopra una puntata: l'avversario aggiunge solo la differenza.

    Piatto iniziale 100, l'avversario punta 50 (piatto attuale 150), hero shova 400.
    Chiamando, l'avversario mette altri 350: il piatto finale è 900, non 950, e
    vincendo sempre hero incassa 900 - 400 = 500.
    """
    ev = calculate_shove_ev(
        hero_equity_if_called=1.0,
        fold_probability=0.0,
        pot_before_shove=150,
        shove_amount=400,
        villain_already_in=50,
    )

    assert ev == pytest.approx(500.0)


def test_shove_into_an_unbet_pot_is_unchanged():
    """Senza una puntata avversaria da assorbire vale il familiare piatto + 2*shove."""
    ev = calculate_shove_ev(
        hero_equity_if_called=1.0, fold_probability=0.0, pot_before_shove=150, shove_amount=400
    )

    assert ev == pytest.approx(150 + 2 * 400 - 400)


def test_shove_ev_rejects_shove_not_bigger_than_the_bet_faced():
    with pytest.raises(InvalidEvInputError):
        calculate_shove_ev(
            hero_equity_if_called=0.5,
            fold_probability=0.5,
            pot_before_shove=150,
            shove_amount=50,
            villain_already_in=50,
        )


def test_shove_ev_rejects_villain_contribution_larger_than_pot():
    with pytest.raises(InvalidEvInputError):
        calculate_shove_ev(
            hero_equity_if_called=0.5,
            fold_probability=0.5,
            pot_before_shove=40,
            shove_amount=200,
            villain_already_in=50,
        )
