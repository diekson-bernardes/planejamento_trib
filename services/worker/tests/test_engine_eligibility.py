"""AT-116, AT-117: elegível, alerta, inelegível e indeterminado."""
import copy
from decimal import Decimal

import pytest

from conftest import accepted_assumptions
from worker.engine.eligibility import ALERTA, ELEGIVEL, INDETERMINADO, INELEGIVEL, evaluate
from worker.engine.snapshot import SnapshotView

pytestmark = pytest.mark.samples
DECLS = ["eleg.socio_pj", "eleg.participacao_receita_global", "eleg.atividade_vedada", "eleg.debitos_sem_suspensao",
         "eleg.obrigatoriedade_real"]


def informed(value="nao"):
    return {(k, "caso"): value for k in DECLS}


def test_all_declared_no_gives_eligible(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    r = evaluate(view, ["2026-08"], accepted_assumptions(view, rules, informed()), rules)
    assert r["SIMPLES"].status == ELEGIVEL
    assert r["PRESUMIDO"].status == ELEGIVEL
    assert r["REAL"].status == ELEGIVEL


def test_not_informed_is_indeterminate(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    r = evaluate(view, ["2026-08"], accepted_assumptions(view, rules), rules)
    assert r["SIMPLES"].status == INDETERMINADO and not r["SIMPLES"].rankable
    assert all(x["motivo"].startswith("Não informado") for x in r["SIMPLES"].reasons)


def test_partner_company_makes_simples_ineligible(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    over = informed()
    over[("eleg.socio_pj", "caso")] = "sim"
    r = evaluate(view, ["2026-08"], accepted_assumptions(view, rules, over), rules)
    assert r["SIMPLES"].status == INELEGIVEL
    assert "eleg.socio_pj" in r["SIMPLES"].reasons[0]["regra"]


def test_presumido_over_78_millions_is_ineligible(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    over = informed()
    over[("presumido.receita_total_ano_anterior", "caso")] = "80000000.00"
    r = evaluate(view, ["2026-08"], accepted_assumptions(view, rules, over), rules)
    assert r["PRESUMIDO"].status == INELEGIVEL


def test_revenue_above_ceiling_by_more_than_20_percent(snapshot_content, rules):
    content = copy.deepcopy(snapshot_content)
    for v in content["values"]:
        if v["doc_type"] == "PGDAS_D" and v["field_key"] == "receita.rba" and v["competence"].startswith("2026-08"):
            v["value"] = Decimal("6000000.00")
    view = SnapshotView(content)
    r = evaluate(view, ["2026-08"], accepted_assumptions(view, rules, informed()), rules)
    assert r["SIMPLES"].status == INELEGIVEL


def test_sublimit_in_effect_is_alert(snapshot_content, rules):
    content = copy.deepcopy(snapshot_content)
    for v in content["values"]:
        if v["doc_type"] == "PGDAS_D" and v["field_key"] == "receita.rbaa" and v["competence"].startswith("2026-08"):
            v["value"] = Decimal("3700000.00")
    view = SnapshotView(content)
    r = evaluate(view, ["2026-08"], accepted_assumptions(view, rules, informed()), rules)
    assert r["SIMPLES"].status == ALERTA
