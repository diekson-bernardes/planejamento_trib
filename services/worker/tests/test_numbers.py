from decimal import Decimal

import pytest

from worker.pdf.numbers import (
    cnpj_is_valid, competence_from_mm_yyyy, is_money, normalize_cnpj, parse_money, signed, split_glued, unglue,
)


@pytest.mark.parametrize("token, value, nature", [
    ("203.180,77C", Decimal("203180.77"), "C"),
    ("****203.180,77C", Decimal("203180.77"), "C"),
    ("*****126.353,14", Decimal("126353.14"), None),
    ("5.161.156,62D", Decimal("5161156.62"), "D"),
    ("0,00", Decimal("0.00"), None),
    ("9,18", Decimal("9.18"), None),
])
def test_parse_money(token, value, nature):
    assert parse_money(token) == (value, nature)


@pytest.mark.parametrize("token", ["=0,0000", "12", "01/2025", "3.1.1.01.001", "abc", "1.2345,00"])
def test_not_money(token):
    assert not is_money(token)


def test_parse_money_rejects_invalid():
    with pytest.raises(ValueError):
        parse_money("12,3")


def test_signed_nature():
    assert signed(Decimal("10"), "C") == Decimal("-10")
    assert signed(Decimal("10"), "D") == Decimal("10")


def test_glued_cells_from_pgdas():
    assert split_glued("92.916,6302/2025") == ("92.916,63", "02/2025")
    assert split_glued("0,0002/2025") == ("0,00", "02/2025")
    assert split_glued("388.487,27") == ("388.487,27", None)
    assert unglue("01/2025 92.916,6302/2025 79.496,47") == "01/2025 92.916,63 02/2025 79.496,47"


def test_competence_and_cnpj():
    assert competence_from_mm_yyyy("08/2026") == "2026-08"
    assert normalize_cnpj("CNPJ Matriz: 37.704.456/0001-42") == "37704456000142"
    assert normalize_cnpj("CNPJ : 37704456000142") == "37704456000142"
    assert cnpj_is_valid("37704456000142")
    assert cnpj_is_valid("11222333000181")
    assert not cnpj_is_valid("11222333000180")
    assert not cnpj_is_valid("11111111111111")
