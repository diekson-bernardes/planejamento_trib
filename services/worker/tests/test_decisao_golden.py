"""AT-222: a Projeção 2026 da amostra reproduz exatamente o golden aprovado pelo responsável de negócio."""
from decimal import Decimal

import pytest

from conftest import golden_assumptions_06_08
from worker.engine.decision import project
from worker.engine.snapshot import SnapshotView

pytestmark = pytest.mark.samples


def test_projection_2026_matches_approved_golden(snapshot_content_06_08, rules, decision_params, golden):
    g = golden("decisao_2026")
    assert g["approved_by"] and g["approved_at"]            # só vale com aprovação registrada
    assert rules.version == g["rules_version"] and decision_params.version == g["decision_version"]
    view = SnapshotView(snapshot_content_06_08)
    res = project(view, golden_assumptions_06_08(view, rules, golden), rules, decision_params, Decimal(g["threshold"]))
    assert res.projected.origins == g["origins"]
    assert res.projected.base["receita_anual"] == g["receita_anual"]
    assert res.simulation.ranking == g["ranking"]
    for regime, expected in g["regimes"].items():
        got = res.simulation.regimes[regime]
        assert str(got.total) == expected["total"], regime
        assert {p: str(v) for p, v in sorted(got.by_period.items())} == expected["by_period"], regime
    rec = res.recommendation.as_dict()
    assert {k: rec[k] for k in g["recomendacao"]} == g["recomendacao"]
    for s in res.sensitivity:
        d, expected = s.as_dict(), g["sensibilidade"][s.key]
        assert {"virada_x": d["virada_x"], "virada_valor": d["virada_valor"], "novo_lider": s.new_leader,
                "robustez": s.robustness, "limite_juridico_x": d["limite_juridico_x"]} == expected, s.key
