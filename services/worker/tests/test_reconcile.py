"""AT-008, AT-009, AT-016: conciliação R1–R6 = golden, tolerância e fonte ausente."""
from decimal import Decimal

import pytest

from conftest import DEFAULT_MAPPINGS
from worker.models import DocType
from worker.pipeline import parse_document
from worker.reconcile import Fact, Facts, previous_competence, reconcile

NAMES = ["pgdas_202606", "pgdas_202607", "pgdas_202608", "folha_202608", "dre_202608", "balancete_202608"]


def facts_from(sample, names=NAMES, adjust=None) -> list[Fact]:
    facts = []
    for name in names:
        result, _ = parse_document(sample(name))
        for v in result.values:
            value = v.value
            if adjust and (result.doc_type, v.field_key, v.column) == adjust[0]:
                value += adjust[1]
            facts.append(Fact(result.doc_type, v.competence, v.field_key, v.column, v.section, value, v.nature))
    return facts


def as_dicts(results):
    return [{"competence": r.competence, "rule": r.rule,
             "left_value": None if r.left_value is None else str(r.left_value),
             "right_value": None if r.right_value is None else str(r.right_value),
             "diff": None if r.diff is None else str(r.diff), "status": r.status} for r in results]


@pytest.mark.samples
def test_reconciliation_matches_golden(sample, golden):
    expected = golden("reconciliation_202608")
    results = reconcile(Facts(facts_from(sample)), DEFAULT_MAPPINGS, Decimal(expected["tolerance"]))
    assert as_dicts(results) == expected["results"]
    august = [r for r in results if r.competence == "2026-08"]
    assert [r.status for r in august] == ["ok"] * 6


@pytest.mark.samples
@pytest.mark.parametrize("delta, status", [(Decimal("0.80"), "ok"), (Decimal("1.00"), "ok"), (Decimal("1.50"), "divergent")])
def test_tolerance_boundary(sample, delta, status):
    facts = facts_from(sample, adjust=((DocType.DRE_ALTERDATA, "conta.4.1.1.01.001", None), delta))
    results = reconcile(Facts(facts), DEFAULT_MAPPINGS, Decimal("1.00"))
    r1 = next(r for r in results if r.competence == "2026-08" and r.rule == "R1")
    assert r1.status == status
    assert abs(r1.diff) == delta


@pytest.mark.samples
def test_missing_payroll_is_missing_source_not_divergent(sample):
    names = [n for n in NAMES if n != "folha_202608"]
    results = reconcile(Facts(facts_from(sample, names)), DEFAULT_MAPPINGS, Decimal("1.00"))
    august = {r.rule: r.status for r in results if r.competence == "2026-08"}
    assert august == {"R1": "ok", "R2": "ok", "R3": "missing_source", "R4": "missing_source",
                      "R5": "missing_source", "R6": "ok"}


def test_without_mapping_everything_is_missing_source():
    facts = [Fact(DocType.PGDAS_D, "2026-08", "receita.rpa", "total", "2.1", Decimal("100"))]
    results = reconcile(Facts(facts), {}, Decimal("1.00"))
    assert {r.status for r in results} == {"missing_source"}


def test_previous_competence():
    assert previous_competence("2026-08") == "2026-07"
    assert previous_competence("2026-01") == "2025-12"
