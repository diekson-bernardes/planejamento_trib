"""Ciclo 4 — motor de 2027: CBS/IBS no lugar de PIS/Cofins, IPI zero, crédito financeiro, Simples híbrido e
2026 intacto. O motor só calcula 2027 sobre meses de 2027: os casos usam a projeção deslocada (snapshot sintético)."""
from decimal import Decimal

import pytest

from conftest import golden_assumptions_06_08, reform_assumptions
from worker.engine import cbs_ibs
from worker.engine.assumptions import Assumptions
from worker.engine.calculate import NAO_CALCULADO, calculate
from worker.engine.decision import project
from worker.engine.memory import HIBRIDO, REGIMES, money, regimes_for
from worker.engine.snapshot import SnapshotView

pytestmark = pytest.mark.samples
THRESHOLD = Decimal("0.05")


@pytest.fixture(scope="module")
def view(snapshot_content_06_08):
    return SnapshotView(snapshot_content_06_08)


@pytest.fixture(scope="module")
def result(view, rules, rules_2027, decision_params, decision_params_2027, golden):
    a = reform_assumptions(view, rules, rules_2027, golden)
    return project(view, a, rules_2027, decision_params_2027, THRESHOLD, base_params=decision_params)


def test_four_alternatives_only_from_2027(rules, rules_2027):
    assert regimes_for(rules) == REGIMES                       # 2026 não muda
    assert regimes_for(rules_2027) == REGIMES + (HIBRIDO,)


def test_no_pis_cofins_ipi_in_2027(result):
    sim = result.simulation
    assert set(sim.regimes) == {"SIMPLES", "PRESUMIDO", "REAL", HIBRIDO}
    assert all(r.status == "calculado" for r in sim.regimes.values())
    taxes = {l.tax for l in sim.lines if l.kind == "tributo"}
    assert not taxes & {"pis", "cofins", "ipi"}
    assert {"cbs", "ibs"} <= taxes


def test_regular_regime_cbs_is_debit_minus_financial_credit(result):
    sim = result.simulation
    for regime in ("PRESUMIDO", "REAL", HIBRIDO):
        line = next(l for l in sim.lines if (l.regime, l.period, l.tax) == (regime, "2027-08", "cbs"))
        credits = Decimal(line.formula.split("créditos ")[1].split(" ×")[0].replace(".", "").replace(",", "."))
        assert line.rate == Decimal("0.095")
        assert line.amount == money(line.base * line.rate - credits * line.rate)
        assert line.origin["aliquota"] is not None


def test_hybrid_takes_cbs_ibs_out_of_das(result):
    sim = result.simulation
    simples, hybrid = sim.regimes["SIMPLES"], sim.regimes[HIBRIDO]
    for tax in ("irpj", "csll", "cpp", "icms"):                 # demais parcelas do DAS iguais
        assert hybrid.by_tax[tax] == simples.by_tax[tax]
    # CBS/IBS pelo regime regular, com o ICMS do próprio DAS fora da base (LC 214, art. 12, § 2º)
    for l in (l for l in sim.lines if (l.regime, l.tax, l.period) == (HIBRIDO, "cbs", "2027-08")):
        icms = sum((x.amount for x in sim.lines if (x.regime, x.tax, x.period) == (HIBRIDO, "icms", "2027-08")), Decimal("0"))
        assert f"ICMS/ISS {icms:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") in l.formula
    assert all(l.rate == Decimal("0.095") for l in sim.lines if l.regime == HIBRIDO and l.tax == "cbs")
    assert simples.by_tax["ibs"] == 0                          # IBS sem parcela no DAS em 2027 (hipótese)


def test_missing_rates_leave_regular_regimes_not_calculated(view, rules, rules_2027, decision_params,
                                                            decision_params_2027, golden):
    a = reform_assumptions(view, rules, rules_2027, golden, reform_values={"reforma.crescimento": "0.05"})
    res = project(view, a, rules_2027, decision_params_2027, THRESHOLD, base_params=decision_params)
    for regime in ("PRESUMIDO", "REAL", HIBRIDO):
        rr = res.simulation.regimes[regime]
        assert rr.status == NAO_CALCULADO
        assert any("alíquota de CBS" in p for p in rr.pending)


def test_credit_balance_is_carried_forward(rules_2027):
    rows = [{"key": "reforma.cbs_aliquota", "scope": "caso", "value": "0.10"},
            {"key": "reforma.ibs_aliquota", "scope": "caso", "value": "0.01"},
            {"key": "reforma.creditos_base", "scope": "competencia:2027-01", "value": "150000.00"},
            {"key": "reforma.creditos_base", "scope": "competencia:2027-02", "value": "0.00"}]
    a, saldo = Assumptions(rows), {}
    jan = {l.tax: l.amount for l in cbs_ibs.month_lines("PRESUMIDO", "2027-01", Decimal("100000"), Decimal("0"),
                                                       a, rules_2027, saldo)}
    assert jan == {"cbs": Decimal("0.00"), "ibs": Decimal("0.00")}
    assert saldo == {"cbs": Decimal("5000.00"), "ibs": Decimal("500.00")}
    feb = {l.tax: l.amount for l in cbs_ibs.month_lines("PRESUMIDO", "2027-02", Decimal("100000"), Decimal("0"),
                                                       a, rules_2027, saldo)}
    assert feb == {"cbs": Decimal("5000.00"), "ibs": Decimal("500.00")}
    assert saldo == {"cbs": 0, "ibs": 0}


def test_2026_calculation_unchanged(view, rules, golden):
    res = calculate(view, golden_assumptions_06_08(view, rules, golden), rules)
    g = golden("motor_202606_08")
    assert {r: str(res.regimes[r].total) for r in g["regimes"]} == {r: v["total"] for r, v in g["regimes"].items()}
    assert HIBRIDO not in res.regimes


def test_legacy_case_without_rates_is_blocked_not_recommended(view, rules, rules_2027, decision_params,
                                                              decision_params_2027, golden):
    """Dossiê com premissas anteriores ao ciclo 4 (sem o grupo reforma_2027): nada pendente, mas sem alíquota os
    regimes regulares não são calculados — a recomendação de 2027 fica bloqueada em vez de escolher o Simples sozinho."""
    a = Assumptions(golden_assumptions_06_08(view, rules, golden).rows
                    + [{"key": "reforma.crescimento", "scope": "caso", "value": "0.05"}])
    res = project(view, a, rules_2027, decision_params_2027, THRESHOLD, base_params=decision_params)
    rec = res.recommendation.as_dict()
    assert rec["status"] == "bloqueado"
    assert any("reforma.cbs_aliquota" in b for b in rec["bloqueios"])
