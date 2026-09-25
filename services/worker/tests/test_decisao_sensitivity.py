"""AT-207, AT-208: ponto de virada por bisseção, "sem virada", limite jurídico e robustez."""
from decimal import Decimal

import pytest

from conftest import golden_assumptions_06_08
from worker.engine.assumptions import Assumptions
from worker.engine.calculate import calculate
from worker.engine.projection import Levers, build_projection
from worker.engine.sensitivity import run_sensitivity
from worker.engine.snapshot import SnapshotView


def test_robustness_bands(decision_params):
    assert decision_params.robustness(Decimal("0.25")) == "robusta"
    assert decision_params.robustness(Decimal("0.10")) == "atencao"
    assert decision_params.robustness(Decimal("0.01")) == "fragil"
    assert decision_params.robustness(None) is None


@pytest.fixture(scope="module")
def sens(snapshot_content_06_08, rules, golden, decision_params):
    view = SnapshotView(snapshot_content_06_08)
    a = golden_assumptions_06_08(view, rules, golden)
    base = build_projection(view, a, decision_params)
    sim = calculate(SnapshotView(base.content), Assumptions(base.assumptions), rules)
    return view, a, {s.key: s for s in run_sensitivity(view, a, rules, decision_params, base, sim.ranking)}


def leader_at(view, a, rules, params, levers):
    pc = build_projection(view, a, params, levers)
    return calculate(SnapshotView(pc.content), Assumptions(pc.assumptions), rules).ranking[0]


@pytest.mark.samples
def test_every_variable_reports_turning_point_or_no_turn(sens):
    _, _, s = sens
    assert set(s) == {"receita", "margem", "folha", "creditos", "icms_iss"}
    for r in s.values():
        d = r.as_dict()
        assert d["lider_base"] == "SIMPLES"
        assert d["sem_virada"] == (d["virada_x"] is None)
        if not d["sem_virada"]:
            assert d["novo_lider"] != "SIMPLES" and d["robustez"] in ("robusta", "atencao", "fragil")
    assert s["creditos"].turning_x is None           # créditos só mexem no Real, distante demais


@pytest.mark.samples
def test_turning_point_is_where_the_leader_changes(sens, rules, decision_params):
    """Pouco antes da virada o líder é o do cenário base; pouco depois, o novo líder."""
    view, a, s = sens
    r = s["receita"]
    eps = Decimal("0.005")
    assert leader_at(view, a, rules, decision_params, Levers(receita=r.turning_x - eps)) == "SIMPLES"
    assert leader_at(view, a, rules, decision_params, Levers(receita=r.turning_x + eps)) == r.new_leader
    assert r.distance == abs(r.turning_x - 1)


@pytest.mark.samples
def test_eligibility_change_is_reported_as_legal_limit(sens):
    """Receita acima do teto do Simples: limite jurídico, não virada de custo (AT-208)."""
    _, _, s = sens
    r = s["receita"]
    assert r.legal_x is not None and r.legal_x > r.turning_x
    assert "SIMPLES" in r.legal_change["elegiveis_base"]
    assert "SIMPLES" not in r.legal_change["elegiveis_alem_do_limite"]
    assert r.legal_value == r.legal_x * r.base_value
