"""AT-111, AT-112, AT-115: Presumido — caso dourado da KB, LC 224/2025 e trimestre parcial."""
from decimal import Decimal

import pytest

from conftest import accepted_assumptions
from worker.engine import presumido
from worker.engine.presumido import QuarterInput, month_pis_cofins, quarter_lines
from worker.engine.snapshot import SnapshotView


def amounts(lines):
    return {l.tax: l.amount for l in lines if l.kind == "tributo"}


def test_kb_golden_trade_quarter(rules):
    lines = quarter_lines(QuarterInput("2026-T1", 3, {"comercio_industria": Decimal("900000.00")}, Decimal("0")), rules)
    got = amounts(lines)
    assert got == {"irpj": Decimal("10800.00"), "adicional_irpj": Decimal("1200.00"), "csll": Decimal("9720.00")}
    pis_cofins = []
    for comp in ("2026-01", "2026-02", "2026-03"):
        pis_cofins += month_pis_cofins(comp, Decimal("300000.00"), rules, "receita")
    totals = {}
    for l in pis_cofins:
        totals[l.tax] = totals.get(l.tax, Decimal("0")) + l.amount
    assert totals == {"pis": Decimal("5850.00"), "cofins": Decimal("27000.00")}
    assert sum(got.values()) + sum(totals.values()) == Decimal("54570.00")


def test_lc224_applies_to_excess_irpj_from_january_csll_from_april(rules):
    rev = {"servicos_gerais": Decimal("2000000.00")}
    q1 = amounts(quarter_lines(QuarterInput("2026-T1", 3, rev, Decimal("0"), excess=Decimal("750000.00"),
                                            irpj_majorado=True, csll_majorado=False), rules))
    # IRPJ: (2.000.000 × 32% + 750.000 × 32% × 10%) = 664.000 × 15%
    assert q1["irpj"] == Decimal("99600.00")
    assert q1["csll"] == Decimal("57600.00")      # 2.000.000 × 32% × 9% (CSLL só a partir de abril)
    q2 = amounts(quarter_lines(QuarterInput("2026-T2", 3, rev, Decimal("0"), excess=Decimal("750000.00"),
                                            irpj_majorado=True, csll_majorado=True), rules))
    assert q2["csll"] == Decimal("59760.00")      # 664.000 × 9%


def test_partial_quarter_uses_months_for_additional(rules):
    lines = quarter_lines(QuarterInput("2026-T3", 1, {"comercio_industria": Decimal("300000.00")}, Decimal("0"),
                                       partial=True), rules)
    got = amounts(lines)
    assert got["adicional_irpj"] == Decimal("400.00")    # (24.000 − 20.000) × 10%
    assert all(l.partial for l in lines)


def test_other_revenue_added_in_full(rules):
    lines = quarter_lines(QuarterInput("2026-T1", 3, {"comercio_industria": Decimal("900000.00")}, Decimal("10000.00")), rules)
    assert amounts(lines)["irpj"] == Decimal("12300.00")   # (72.000 + 10.000) × 15%


@pytest.mark.samples
def test_pis_and_cofins_zeroed_independently_and_base_never_negative(snapshot_content, rules):
    """Monofásico só de PIS não isenta a Cofins; exclusão acima da receita zera o tributo sem reduzir o total."""
    view = SnapshotView(snapshot_content)
    acts = view.activities("2026-08")
    receita = sum((act.receita for act in acts), Decimal("0"))
    only_pis = {("atividade.tributos_zerados", "atividade:" + act.key): ["pis"] for act in acts}
    lines = presumido.calculate(["2026-08"], view, accepted_assumptions(view, rules, only_pis), rules)
    base = {l.tax: l.base for l in lines if l.tax in ("pis", "cofins")}
    assert base["pis"] == Decimal("0.00") and base["cofins"] == receita.quantize(Decimal("0.01"))

    huge = {("pis_cofins_exclusoes", "competencia:2026-08"): "999999999.00"}
    lines = presumido.calculate(["2026-08"], view, accepted_assumptions(view, rules, huge), rules)
    assert {l.tax: l.amount for l in lines if l.tax in ("pis", "cofins")} == {"pis": Decimal("0.00"), "cofins": Decimal("0.00")}
