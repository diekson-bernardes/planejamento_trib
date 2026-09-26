"""Ciclo 4 — decisão de 2027: projeção de 2026 deslocada com crescimento, bloqueio só do próprio exercício,
sensibilidade com a alíquota da CBS e tempo ≤ 60 s."""
import time
from decimal import Decimal

import pytest

from conftest import reform_assumptions
from worker.engine.decision import project
from worker.engine.memory import HIBRIDO
from worker.engine.projection import build_projection
from worker.engine.snapshot import SnapshotView
from worker.pipeline import blocking

THRESHOLD = Decimal("0.05")


@pytest.fixture(scope="module")
def case(snapshot_content_06_08, rules, rules_2027, golden):
    view = SnapshotView(snapshot_content_06_08)
    return view, reform_assumptions(view, rules, rules_2027, golden)


@pytest.fixture(scope="module")
def result(case, rules_2027, decision_params, decision_params_2027):
    view, a = case
    started = time.monotonic()
    res = project(view, a, rules_2027, decision_params_2027, THRESHOLD, base_params=decision_params)
    return res, time.monotonic() - started


@pytest.mark.samples
def test_2027_is_2026_projection_shifted_with_growth(case, result, decision_params):
    view, a = case
    res, elapsed = result
    assert elapsed <= 60
    base = res.projected.base
    assert (res.projected.year, base["ano_base"], base["crescimento"]) == (2027, 2026, "0.05")
    receita_2026 = Decimal(build_projection(view, a, decision_params).base["receita_anual"])
    assert abs(Decimal(base["receita_anual"]) - receita_2026 * Decimal("1.05")) <= Decimal("0.12")
    assert sorted(res.projected.origins) == [f"2027-{m:02d}" for m in range(1, 13)]
    assert set(res.projected.origins.values()) == {"projetado"}
    assert len(res.simulation.ranking) == 4 and HIBRIDO in res.simulation.ranking
    assert any("crescimento de 5,00%" in c for c in res.recommendation.as_dict()["ressalvas"])


@pytest.mark.samples
def test_sensitivity_has_cbs_rate_variable(result, decision_params_2027):
    res, _ = result
    assert [v.key for v in decision_params_2027.variables][-1] == "cbs"
    sens = {s.key: s.as_dict() for s in res.sensitivity}
    assert len(sens) == 6
    assert sens["cbs"]["unidade"] == "fracao"
    assert "unidade" not in sens["receita"]                   # as_dict de 2026 inalterado (hashes do ciclo 3)


@pytest.mark.samples
def test_consumption_load_includes_cbs_ibs(result):
    res, _ = result
    rec, sim = res.recommendation.as_dict(), res.simulation
    for regime in ("PRESUMIDO", HIBRIDO):
        by_tax = sim.regimes[regime].by_tax
        expected = sum((by_tax.get(t, Decimal("0")) for t in ("icms", "iss", "cbs", "ibs")), Decimal("0"))
        assert Decimal(rec["carga"][regime]["consumo"]) == expected


def test_reform_pending_blocks_only_2027():
    rows = [{"key": "reforma.cbs_aliquota", "status": "pending", "grp": "reforma_2027"},
            {"key": "folha.rat", "status": "confirmed", "grp": "folha"}]
    assert blocking(rows, 2026) == []
    assert [r["key"] for r in blocking(rows, 2027)] == ["reforma.cbs_aliquota"]
    rows.append({"key": "folha.fap", "status": "pending", "grp": "folha"})
    assert [r["key"] for r in blocking(rows, 2026)] == ["folha.fap"]


@pytest.mark.samples
def test_credit_base_follows_revenue_lever(case, decision_params, decision_params_2027):
    """A base de créditos de 2027 acompanha a receita (como os campos proporcionais de 2026): sob a alavanca de
    receita a razão créditos/receita é a do dado, não a do cenário."""
    from dataclasses import replace

    from worker.engine.projection import Levers, shift_year

    view, a = case

    def credits(x: str) -> Decimal:
        lv = Levers(receita=Decimal(x))
        pc = shift_year(build_projection(view, a, decision_params, replace(lv, cbs=Decimal("1"))),
                        decision_params_2027, Decimal("0.05"), lv)
        return sum((Decimal(r["value"]) for r in pc.assumptions if r["key"] == "reforma.creditos_base"), Decimal("0"))

    assert abs(credits("0.6") - credits("1") * Decimal("0.6")) <= Decimal("0.12")


@pytest.mark.samples
def test_reform_suggestions_are_all_in_their_own_group(case, rules, rules_2027):
    """Tudo o que só existe em 2027 (alíquotas, crescimento, créditos, custo do híbrido) fica no grupo reforma_2027:
    pendente, não bloqueia o cálculo de 2026. Créditos vêm do Livro (CFOPs creditáveis) quando há Livro no mês."""
    from worker.engine.assumptions import REFORM_GROUP, suggest

    view, _ = case
    extra = [s for s in suggest(view, rules, None, rules_2027) if s not in suggest(view, rules)]
    assert extra and all(s.group == REFORM_GROUP for s in extra)
    assert any(s.scope == "regime:SIMPLES_HIBRIDO" for s in extra)
    aug = next(s for s in extra if (s.key, s.scope) == ("reforma.creditos_base", "competencia:2026-08"))
    assert aug.origin["doc_type"] == "LIVRO_ICMS_ALTERDATA" and "2353" in aug.origin["cfops"]
