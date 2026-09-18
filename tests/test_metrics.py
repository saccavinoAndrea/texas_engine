import pytest

from engine.metrics import (
    InvalidMetricsInputError,
    calculate_max_implied_bet,
    calculate_mdf,
    calculate_spr,
)


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


def test_mdf_pot_sized_bet_is_one_half():
    """Il piatto va passato come lo inserisce l'utente, cioè già comprensivo della
    puntata da chiamare: qui l'avversario ha puntato 100 in un piatto di 100, quindi
    il piatto inserito è 200. La definizione dà 100/(100+100) = 50%; usare per errore
    il piatto comprensivo come piatto precedente darebbe 66,7%."""
    assert calculate_mdf(pot_before_call=200, amount_to_call=100) == pytest.approx(0.5)


def test_mdf_half_pot_bet():
    # Puntata di 50 in un piatto di 100 -> piatto inserito 150, MDF = 100/150
    assert calculate_mdf(pot_before_call=150, amount_to_call=50) == pytest.approx(2 / 3)


def test_mdf_matches_definition_across_bet_sizes():
    """Controprova diretta sulla definizione, per varie size."""
    for pot_before_bet, bet in [(100, 25), (100, 50), (100, 100), (100, 200), (60, 15)]:
        expected = pot_before_bet / (pot_before_bet + bet)
        assert calculate_mdf(pot_before_call=pot_before_bet + bet, amount_to_call=bet) == pytest.approx(expected)


def test_mdf_rejects_zero_bet_size():
    with pytest.raises(InvalidMetricsInputError):
        calculate_mdf(pot_before_call=100, amount_to_call=0)


def test_mdf_rejects_call_larger_than_pot_that_contains_it():
    with pytest.raises(InvalidMetricsInputError):
        calculate_mdf(pot_before_call=100, amount_to_call=150)


def test_mdf_rejects_negative_amounts():
    with pytest.raises(InvalidMetricsInputError):
        calculate_mdf(pot_before_call=-1, amount_to_call=50)
    with pytest.raises(InvalidMetricsInputError):
        calculate_mdf(pot_before_call=100, amount_to_call=-1)


def test_max_implied_bet_is_stack_left_after_call():
    assert calculate_max_implied_bet(effective_stack=200, amount_to_call=50) == pytest.approx(150.0)


def test_max_implied_bet_clamps_to_zero_when_call_exceeds_stack():
    # Non ha senso un tetto negativo: se il call "esaurisce" lo stack (es. è uno shove),
    # non resta nulla da vincere in più nei giri successivi.
    assert calculate_max_implied_bet(effective_stack=50, amount_to_call=80) == 0.0


def test_max_implied_bet_rejects_negative_amounts():
    with pytest.raises(InvalidMetricsInputError):
        calculate_max_implied_bet(effective_stack=-1, amount_to_call=50)
    with pytest.raises(InvalidMetricsInputError):
        calculate_max_implied_bet(effective_stack=100, amount_to_call=-1)
