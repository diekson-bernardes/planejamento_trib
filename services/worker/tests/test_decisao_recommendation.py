"""AT-209 a AT-213: recomendado, inconclusivo, bloqueado, inelegível fora do ranking e conformidade à parte."""
from decimal import Decimal

from worker.engine.assumptions import Assumptions
from worker.engine.calculate import CALCULADO, NAO_CALCULADO, RegimeResult, SimulationResult
from worker.engine.eligibility import ELEGIVEL, INELEGIVEL, EligibilityResult
from worker.engine.recommendation import BLOQUEADO, INCONCLUSIVO, RECOMENDADO, recommend

D = Decimal


def sim(totals: dict, ineligible=(), not_calculated=()) -> SimulationResult:
    regimes, elig = {}, {}
    for r, (total, by_tax) in totals.items():
        rr = RegimeResult(r, total=D(total), by_tax={k: D(v) for k, v in by_tax.items()})
        if r in not_calculated:
            rr.status = NAO_CALCULADO
            rr.pending = ["sem regra"]
        regimes[r] = rr
        e = EligibilityResult(r)
        if r in ineligible:
            e.add(INELEGIVEL, "Declarado: sócio PJ", "elegibilidade.simples.eleg.socio_pj@2026.1.0")
        elig[r] = e
    ranking = sorted((r for r in regimes if regimes[r].status == CALCULADO and elig[r].rankable),
                     key=lambda r: regimes[r].total)
    return SimulationResult(["2026-01"], [], elig, regimes, ranking, [], [], "2026.1.0")


BASE = {
    "SIMPLES": ("100000.00", {"irpj": "10000", "cofins": "30000", "cpp": "40000", "icms": "20000"}),
    "PRESUMIDO": ("112000.00", {"irpj": "30000", "cofins": "32000", "cpp": "30000", "icms": "20000"}),
    "REAL": ("150000.00", {"irpj": "60000", "cofins": "40000", "cpp": "30000", "icms": "20000"}),
}


def test_difference_above_threshold_is_recommended(decision_params):
    r = recommend(sim(BASE), [], Assumptions([]), decision_params, D("0.05"), D("1000000"), "SIMPLES", [])
    assert r.status == RECOMENDADO and r.regime == "SIMPLES" and r.second == "PRESUMIDO"
    assert r.text.startswith("Recomendamos o Simples Nacional porque")
    assert r.savings_vs_second == D("12000.00") and r.savings_vs_second_pct == D("0.1200")
    assert r.savings_vs_current == D("0.00")
    assert [f["tributo"] for f in r.factors] == ["irpj", "cofins"]     # só tributos em que o vencedor paga menos
    assert r.loads["SIMPLES"] == {"consumo": D("50000.00"), "renda": D("10000.00"), "folha": D("40000.00")}
    assert r.effective_rates["SIMPLES"] == D("0.1000")


def test_difference_below_threshold_is_inconclusive(decision_params):
    r = recommend(sim(BASE), [], Assumptions([]), decision_params, D("0.15"), D("1000000"), "SIMPLES", [])
    assert r.status == INCONCLUSIVO and r.text.startswith("Resultado inconclusivo")


def test_missing_critical_data_blocks_with_preview(decision_params):
    r = recommend(sim(BASE), [], Assumptions([]), decision_params, D("0.05"), D("1000000"), "SIMPLES",
                  ["3 premissa(s) pendente(s) de confirmação"])
    assert r.status == BLOQUEADO and "Prévia incompleta" in r.text
    assert r.loads          # a prévia continua com os números calculados


def test_ineligible_and_not_calculated_regimes_leave_the_ranking(decision_params):
    s = sim(BASE, ineligible=("SIMPLES",), not_calculated=("REAL",))
    r = recommend(s, [], Assumptions([]), decision_params, D("0.05"), D("1000000"), "SIMPLES", [])
    assert r.regime == "PRESUMIDO" and r.status == RECOMENDADO and r.second is None
    assert {e["regime"]: e["motivo"] for e in r.excluded} == {"SIMPLES": "inelegível", "REAL": "não calculado"}
    assert "sócio PJ" in r.excluded[0]["detalhe"][0]
    assert r.savings_vs_current is None          # regime atual inelegível


def test_compliance_cost_is_shown_but_never_changes_the_ranking(decision_params):
    rows = [{"key": "conformidade.custo_anual", "scope": "regime:SIMPLES", "value": "50000.00"},
            {"key": "conformidade.custo_anual", "scope": "regime:PRESUMIDO", "value": "0.00"}]
    r = recommend(sim(BASE), [], Assumptions(rows), decision_params, D("0.05"), D("1000000"), "SIMPLES", [])
    assert r.regime == "SIMPLES"
    assert r.compliance == {"SIMPLES": D("50000.00"), "PRESUMIDO": D("0.00")}


def test_no_eligible_regime_blocks(decision_params):
    s = sim(BASE, ineligible=("SIMPLES", "PRESUMIDO", "REAL"))
    r = recommend(s, [], Assumptions([]), decision_params, D("0.05"), D("1000000"), "SIMPLES", [])
    assert r.status == BLOQUEADO and "nenhum regime elegível" in r.blockers[0]
