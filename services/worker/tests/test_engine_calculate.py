"""AT-101, AT-118, AT-120, AT-121, AT-123, AT-126: orquestração, memória, idempotência e golden aprovado."""
import copy
from decimal import Decimal

import pytest

from conftest import accepted_assumptions
from worker.engine.calculate import NAO_CALCULADO, NoCompleteCompetence, calculate
from worker.engine.snapshot import SnapshotView

pytestmark = pytest.mark.samples


def golden_assumptions(view, rules, golden):
    g = golden("motor_202608")
    return accepted_assumptions(view, rules, {(k, "caso"): v for k, v in g["assumption_overrides"].items()}), g


def test_complete_competences(snapshot_content):
    view = SnapshotView(snapshot_content)
    assert view.complete_competences() == ["2026-08"]
    assert view.excluded_competences() == ["2026-06", "2026-07"]


def test_matches_approved_golden(snapshot_content, rules, golden):
    view = SnapshotView(snapshot_content)
    a, g = golden_assumptions(view, rules, golden)
    assert g["approved_by"] and g["approved_at"]          # AT-126: só vale com aprovação registrada
    res = calculate(view, a, rules)
    assert res.rules_version == g["rules_version"]
    assert res.competences == g["competences"]
    assert res.ranking == g["ranking"]
    for regime, expected in g["regimes"].items():
        got = res.regimes[regime]
        assert str(got.total) == expected["total"], regime
        assert {k: str(v) for k, v in sorted(got.by_tax.items())} == expected["by_tax"], regime
        assert got.partial_periods == expected["partial_periods"], regime


def test_simples_total_equals_declared_das(snapshot_content, rules, golden):
    view = SnapshotView(snapshot_content)
    a, _ = golden_assumptions(view, rules, golden)
    res = calculate(view, a, rules)
    assert res.regimes["SIMPLES"].total == Decimal("23430.47")


def test_every_line_has_rule_and_origin(snapshot_content, rules, golden):
    view = SnapshotView(snapshot_content)
    a, _ = golden_assumptions(view, rules, golden)
    res = calculate(view, a, rules)
    assert res.lines
    for line in res.lines:
        assert line.rule_ref.endswith("@" + rules.version)
        assert line.formula
        if line.kind == "tributo" and line.tax not in ("rbt12",):
            assert line.origin, (line.regime, line.tax)


def test_same_inputs_same_hash(snapshot_content, rules, golden):
    view = SnapshotView(snapshot_content)
    a, _ = golden_assumptions(view, rules, golden)
    assert calculate(view, a, rules).result_hash == calculate(view, a, rules).result_hash


def test_changed_assumption_changes_hash(snapshot_content, rules, golden):
    view = SnapshotView(snapshot_content)
    a, _ = golden_assumptions(view, rules, golden)
    b = accepted_assumptions(view, rules, {("folha.rat", "caso"): "0.03"})
    assert calculate(view, a, rules).result_hash != calculate(view, b, rules).result_hash


def test_indeterminate_regimes_are_not_ranked(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    res = calculate(view, accepted_assumptions(view, rules), rules)   # declarações "não informado"
    assert res.ranking == ["REAL"]
    assert res.eligibility["SIMPLES"].status == "indeterminado"


def test_missing_rule_means_not_calculated(snapshot_content, rules):
    content = copy.deepcopy(snapshot_content)
    for item in content["files"] + content["values"]:
        item["competence"] = item["competence"].replace("2026-", "2027-")
    view = SnapshotView(content)
    res = calculate(view, accepted_assumptions(view, rules), rules)
    assert {r.status for r in res.regimes.values()} == {NAO_CALCULADO}
    assert all("sem regras vigentes" in r.pending[0] for r in res.regimes.values())
    assert res.ranking == []


def test_missing_profile_means_not_calculated(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    act = view.activities("2026-08")[0]
    a = accepted_assumptions(view, rules, {("atividade.perfil", "atividade:" + act.key): None})
    res = calculate(view, a, rules)
    assert res.regimes["SIMPLES"].status == NAO_CALCULADO
    assert "sem perfil" in res.regimes["SIMPLES"].pending[0]


def test_no_complete_competence_raises(snapshot_content, rules):
    content = copy.deepcopy(snapshot_content)
    content["files"] = [f for f in content["files"] if f["doc_type"] != "DRE_ALTERDATA"]
    view = SnapshotView(content)
    with pytest.raises(NoCompleteCompetence):
        calculate(view, accepted_assumptions(view, rules), rules)
