"""AT-113, AT-114: Real — caso dourado da KB, prejuízo, parcela cumulativa e reclassificação do lucro."""
from decimal import Decimal

import pytest

from conftest import accepted_assumptions
from worker.engine import real
from worker.engine.real import QuarterProfit, quarter_lines
from worker.engine.snapshot import SnapshotView


def amounts(lines):
    return {l.tax: l.amount for l in lines if l.kind == "tributo"}


def test_kb_golden_quarter_with_loss_compensation(rules):
    q = QuarterProfit("2026-T1", 3, lucro_antes=Decimal("200000.00"), adicoes=Decimal("20000.00"),
                      exclusoes=Decimal("10000.00"), saldo_prejuizo=Decimal("150000.00"),
                      saldo_base_negativa=Decimal("150000.00"))
    out = quarter_lines(q, rules)
    got = amounts(out.lines)
    assert got == {"irpj": Decimal("22050.00"), "adicional_irpj": Decimal("8700.00"), "csll": Decimal("13230.00")}
    assert sum(got.values()) == Decimal("43980.00")
    assert out.saldo_prejuizo == Decimal("87000.00")
    comp = [l for l in out.lines if l.tax == "compensacao_irpj"][0]
    assert comp.amount == Decimal("63000.00")


def test_negative_profit_generates_loss(rules):
    out = quarter_lines(QuarterProfit("2026-T1", 3, Decimal("-50000.00"), Decimal("0"), Decimal("0"),
                                      Decimal("10000.00"), Decimal("0")), rules)
    assert amounts(out.lines) == {"irpj": Decimal("0.00"), "adicional_irpj": Decimal("0.00"), "csll": Decimal("0.00")}
    assert out.saldo_prejuizo == Decimal("60000.00")


@pytest.mark.samples
def test_cumulative_revenue_stays_at_365_in_real(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    acts = view.activities("2026-08")
    overrides = {}
    for act in acts:
        overrides[("atividade.perfil", "atividade:" + act.key)] = {
            "anexo": "III", "presumido": "servicos_hospitalares", "cumulativo_no_real": True, "fator_r": False}
    a = accepted_assumptions(view, rules, overrides)
    lines = real.month_pis_cofins("2026-08", view, a, rules)
    receita = sum((act.receita for act in acts), Decimal("0"))
    cum = [l for l in lines if "cumulativo" in l.formula]
    assert {l.tax: l.amount for l in cum} == {
        "pis": (receita * Decimal("0.0065")).quantize(Decimal("0.01")),
        "cofins": (receita * Decimal("0.03")).quantize(Decimal("0.01")),
    }


@pytest.mark.samples
def test_profit_reclassification_adds_back_simples(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    a = accepted_assumptions(view, rules)
    lines = real.calculate(["2026-08"], view, a, rules)
    rec = [l for l in lines if l.kind == "reclassificacao"][0]
    assert "lucro da DRE 126.353,14" in rec.formula and "despesa de Simples 23.430,47" in rec.formula
    assert rec.origin["lucro"]["field_key"] == "resultado.lucro_liquido"


@pytest.mark.samples
def test_credit_surplus_carries_to_next_month(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    a = accepted_assumptions(view, rules)
    saldo = {"pis": Decimal("1000000"), "cofins": Decimal("1000000")}
    lines = real.month_pis_cofins("2026-08", view, a, rules, saldo)
    assert all(l.amount == 0 for l in lines)
    assert 0 < saldo["pis"] < Decimal("1000000") and 0 < saldo["cofins"] < Decimal("1000000")   # débito do mês abatido
    assert all("saldo credor anterior" in l.formula and "transportado" in l.formula for l in lines)


@pytest.mark.samples
def test_exclusions_reduce_cumulative_base(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    acts = view.activities("2026-08")
    overrides = {("pis_cofins_exclusoes", "competencia:2026-08"): "1000.00"}
    for act in acts:
        overrides[("atividade.perfil", "atividade:" + act.key)] = {
            "anexo": "III", "presumido": "servicos_hospitalares", "cumulativo_no_real": True, "fator_r": False}
    a = accepted_assumptions(view, rules, overrides)
    lines = real.month_pis_cofins("2026-08", view, a, rules)
    receita = sum((act.receita for act in acts), Decimal("0"))
    cum = [l for l in lines if "cumulativo" in l.formula]
    assert {l.base for l in cum} == {(receita - Decimal("1000.00")).quantize(Decimal("0.01"))}


@pytest.mark.samples
def test_real_zeroes_pis_and_cofins_independently(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    acts = view.activities("2026-08")
    overrides = {("pis_cofins_creditos_base", "competencia:2026-08"): "0.00"}
    for act in acts:
        overrides[("atividade.tributos_zerados", "atividade:" + act.key)] = ["cofins"]
    lines = real.month_pis_cofins("2026-08", view, accepted_assumptions(view, rules, overrides), rules)
    receita = sum((act.receita for act in acts), Decimal("0")).quantize(Decimal("0.01"))
    assert {l.tax: l.base for l in lines} == {"pis": receita, "cofins": Decimal("0.00")}
