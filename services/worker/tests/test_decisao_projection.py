"""AT-201 a AT-206, AT-223: projeção do exercício como snapshot sintético lido pelo motor sem alteração."""
import copy
from decimal import Decimal

import pytest

from conftest import golden_assumptions_06_08
from worker.engine.assumptions import Assumptions
from worker.engine.calculate import calculate
from worker.engine.decision import project
from worker.engine.projection import Levers, ProjectionError, build_projection
from worker.engine.snapshot import SnapshotView

pytestmark = pytest.mark.samples


@pytest.fixture(scope="module")
def case(snapshot_content_06_08, rules, golden):
    view = SnapshotView(snapshot_content_06_08)
    return view, golden_assumptions_06_08(view, rules, golden)


def run(pc, rules):
    return calculate(SnapshotView(pc.content), Assumptions(pc.assumptions), rules)


def test_months_are_labeled_by_origin(case, decision_params):
    view, a = case
    pc = build_projection(view, a, decision_params)
    assert pc.origins == {
        **{f"2026-{m:02d}": "estimado" for m in range(1, 6)},
        **{f"2026-{m:02d}": "realizado" for m in range(6, 9)},
        **{f"2026-{m:02d}": "projetado" for m in range(9, 13)},
    }
    assert SnapshotView(pc.content).complete_competences() == [f"2026-{m:02d}" for m in range(1, 13)]


def test_realized_months_reproduce_the_cycle2_golden(case, rules, decision_params, golden):
    """Contrato: os meses realizados entram no motor exatamente como no snapshot homologado (AT-223)."""
    view, a = case
    res = run(build_projection(view, a, decision_params), rules)
    expected = golden("motor_202606_08")["regimes"]["SIMPLES"]["by_period"]
    assert {m: str(res.regimes["SIMPLES"].by_period[m]) for m in expected} == expected
    assert res.alerts == []          # RBT12 sintético = recalculado (sem divergência de centavos)


def test_estimated_months_use_pgdas_series_and_proportional_premises(case, decision_params):
    view, a = case
    pc = build_projection(view, a, decision_params)
    synth = SnapshotView(pc.content)
    serie = view.pgdas_series("2026-08", "receita_anterior")
    assert synth.value("PGDAS_D", "2026-03", "receita.rpa", "total") == serie["2026-03"]
    ratio = Decimal(pc.base["razoes"]["icms_regime_normal"])
    icms = next(Decimal(r["value"]) for r in pc.assumptions
                if r["key"] == "icms_regime_normal" and r["scope"] == "competencia:2026-03")
    assert abs(icms - ratio * serie["2026-03"]) <= serie["2026-03"] * Decimal("0.000001") + Decimal("0.01")


def test_budget_replaces_average_and_marks_origin(case, decision_params, rules, golden):
    view, _ = case
    rows = golden_assumptions_06_08(view, rules, golden).rows
    rows = [dict(r) for r in rows]
    for r in rows:
        if r["key"] == "projecao.receita" and r["scope"] == "competencia:2026-10":
            r["suggested_value"], r["value"] = r["value"], "500000.00"
    pc = build_projection(view, Assumptions(rows), decision_params)
    assert pc.origins["2026-10"] == "orcamento" and pc.origins["2026-11"] == "projetado"
    assert SnapshotView(pc.content).value("PGDAS_D", "2026-10", "receita.rpa", "total") == Decimal("500000.00")


def test_projected_revenue_crossing_the_sublimit_takes_ICMS_out_of_the_DAS(case, decision_params, rules):
    """AT-206: receita +35% (≈ R$ 4,73 mi no ano): o acumulado até novembro passa de R$ 4,32 mi e o ICMS sai
    do DAS em dezembro (mês seguinte ao excesso); com +40% o RBT12 passa do teto e o Simples não é calculado."""
    view, a = case
    res = run(build_projection(view, a, decision_params, Levers(receita=Decimal("1.35"))), rules)
    out_of_das = sorted({l.period for l in res.lines if l.regime == "SIMPLES" and "fora do DAS" in l.formula})
    assert out_of_das == ["2026-12"]
    assert any("Sublimite" in r["motivo"] for r in res.eligibility["SIMPLES"].as_dict()["reasons"])


def test_projection_is_idempotent(case, rules, decision_params):
    """AT-205: mesmas entradas → mesmo hash do resultado."""
    view, a = case
    first = project(view, a, rules, decision_params, Decimal("0.05"))
    second = project(view, a, rules, decision_params, Decimal("0.05"))
    assert first.result_hash == second.result_hash
    assert all(l["origin"].get("mes_origem") for l in first.lines())
    quarterly = [l for l in first.lines() if l["period"] == "2026-T1"]
    assert quarterly and quarterly[0]["origin"]["mes_origem"] == "estimado"


def test_projection_requires_a_complete_competence(snapshot_content_06_08, decision_params):
    content = copy.deepcopy(snapshot_content_06_08)
    content["files"] = [f for f in content["files"] if f["doc_type"] == "PGDAS_D"]
    with pytest.raises(ProjectionError):
        build_projection(SnapshotView(content), Assumptions([]), decision_params)
