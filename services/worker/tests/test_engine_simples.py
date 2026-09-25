"""AT-107 a AT-110: DAS recalculado = PGDAS-D ao centavo, faixa 5 para ICMS, ST e Fator R."""
from decimal import Decimal

import pytest

from conftest import accepted_assumptions
from worker.engine.rules import MissingRule
from worker.engine.simples import band_rates, calculate_month, effective_rate
from worker.engine.snapshot import SnapshotView

TAXES = {"irpj": "irpj", "csll": "csll", "cofins": "cofins", "pis": "pis", "cpp": "inss_cpp", "icms": "icms"}
pytestmark = pytest.mark.samples


def das_by_tax(lines):
    out = {}
    for line in lines:
        if line.kind == "tributo":
            out[line.tax] = out.get(line.tax, Decimal("0")) + line.amount
    return out


@pytest.mark.parametrize("comp", ["2026-06", "2026-07", "2026-08"])
def test_das_equals_declared_pgdas(snapshot_content, rules, comp):
    view = SnapshotView(snapshot_content)
    a = accepted_assumptions(view, rules, extra_months=("2026-06", "2026-07"))
    lines, alerts = calculate_month(comp, view, a, rules)
    calc = das_by_tax(lines)
    for tax, pgdas_col in TAXES.items():
        declared = view.value("PGDAS_D", comp, "tributo." + pgdas_col, pgdas_col, "2.8.total_declarado")
        assert abs(calc.get(tax, Decimal("0")) - declared) <= Decimal("0.01"), (comp, tax)
    total = view.value("PGDAS_D", comp, "tributo.total", "total", "2.8.total_declarado")
    assert abs(sum(calc.values()) - total) <= Decimal("0.01")
    assert alerts == []   # RBT12 recalculado = declarado


def test_band6_icms_uses_band5(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    a = accepted_assumptions(view, rules, extra_months=("2026-06",))
    lines, _ = calculate_month("2026-06", view, a, rules)
    icms = [l for l in lines if l.tax == "icms" and l.kind == "tributo"]
    assert len(icms) == 1                       # só a atividade sem ST
    assert "faixa6_icms_iss_pela_faixa5" in icms[0].rule_ref
    assert icms[0].amount == Decimal("7410.40")
    assert icms[0].verified is False            # regra observada, dispositivo não localizado


def test_st_activity_has_no_icms(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    a = accepted_assumptions(view, rules)
    lines, _ = calculate_month("2026-08", view, a, rules)
    st = [act for act in view.activities("2026-08") if "Com substituição" in act.description][0]
    assert not [l for l in lines if l.activity == st.key and l.tax == "icms"]


def test_fator_r_chooses_annex(rules):
    rbt12 = Decimal("600000")
    iii, band, efetiva = band_rates("III", rbt12, rules, set(), False)
    assert band.faixa == 3 and effective_rate(rbt12, band).quantize(Decimal("0.0001")) == Decimal("0.1056")
    v, band_v, _ = band_rates("V", rbt12, rules, set(), False)
    assert effective_rate(rbt12, band_v).quantize(Decimal("0.0001")) == Decimal("0.1785")


def test_fator_r_line_in_memory(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    act = view.activities("2026-08")[0]
    scope = "atividade:" + act.key
    profile = {"anexo": "V", "presumido": "servicos_gerais", "cumulativo_no_real": False, "fator_r": True}
    a = accepted_assumptions(view, rules, {
        ("atividade.perfil", scope): profile,
        ("atividade.tributos_zerados", scope): [],
        ("folha.folha_12m", "competencia:2026-08"): "1200000.00",   # ~31% do RBT12 → Anexo III
    })
    lines, _ = calculate_month("2026-08", view, a, rules)
    fr = [l for l in lines if l.tax == "fator_r"]
    assert fr and "Anexo III" in fr[0].formula
    assert any(l.activity == act.key and "anexo_III" in l.rule_ref for l in lines if l.kind == "tributo")


def test_fator_r_without_payroll_premise_is_not_silently_annex_v(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    act = view.activities("2026-08")[0]
    profile = {"anexo": "V", "presumido": "servicos_gerais", "cumulativo_no_real": False, "fator_r": True}
    a = accepted_assumptions(view, rules, {("atividade.perfil", "atividade:" + act.key): profile})
    with pytest.raises(MissingRule, match="Fator R"):
        calculate_month("2026-08", view, a, rules)


def test_iss_capped_at_5_percent_in_band5(rules):
    rbt12 = Decimal("3500000")          # Anexo III faixa 5: efetiva ≈ 17,41% > 14,92537%
    rates, band, efetiva = band_rates("III", rbt12, rules, set(), False)
    by_tax = {t: r for t, r, *_ in rates}
    assert by_tax["iss"] == Decimal("0.05")
    assert abs(sum(by_tax.values()) - efetiva) < Decimal("0.0000001")
