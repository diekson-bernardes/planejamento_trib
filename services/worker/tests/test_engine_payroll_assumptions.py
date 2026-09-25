"""AT-103, AT-119: sugestões com origem, hash de premissas e encargos por regime."""
from decimal import Decimal

import pytest

from conftest import accepted_assumptions
from worker.engine.assumptions import assumptions_hash, confirm_all_suggested, suggest
from worker.engine.payroll import charges
from worker.engine.snapshot import SnapshotView

pytestmark = pytest.mark.samples


def test_suggestions_cover_catalog_with_origin(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    sugg = suggest(view, rules)
    keys = {s.key for s in sugg}
    assert {"atividade.perfil", "atividade.tributos_zerados", "icms_regime_normal", "iss_regime_normal",
            "outras_receitas", "pis_cofins_exclusoes", "pis_cofins_creditos_base", "real.adicoes", "real.exclusoes",
            "real.saldo_prejuizo_fiscal", "real.saldo_base_negativa_csll", "folha.rat", "folha.fap",
            "folha.terceiros", "presumido.receita_total_ano_anterior", "eleg.socio_pj"} <= keys
    assert all(s.origin for s in sugg)
    by = {(s.key, s.scope): s for s in sugg}
    assert by[("pis_cofins_creditos_base", "competencia:2026-08")].suggested_value == "149985.71"
    assert by[("pis_cofins_creditos_base", "competencia:2026-08")].origin["accounts"] == ["13101"]
    assert by[("icms_regime_normal", "competencia:2026-08")].suggested_value == "4711.85"
    zero = [s for s in sugg if s.key == "atividade.tributos_zerados"]
    assert sorted(tuple(s.suggested_value) for s in zero) == [(), ("icms",)]


def test_assumptions_hash_is_order_independent_and_value_sensitive(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    rows = confirm_all_suggested(suggest(view, rules))
    assert assumptions_hash(rows) == assumptions_hash(list(reversed(rows)))
    changed = [dict(r) for r in rows]
    changed[0]["value"] = "0.01"
    assert assumptions_hash(changed) != assumptions_hash(rows)


def test_payroll_charges_regular_regimes(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    a = accepted_assumptions(view, rules)
    lines = {l.tax: l for l in charges("PRESUMIDO", "2026-08", view, a, rules)}
    base = Decimal("33831.70")
    assert lines["cpp"].amount == (base * Decimal("0.20")).quantize(Decimal("0.01"))
    assert lines["rat"].amount == (base * Decimal("0.02")).quantize(Decimal("0.01"))
    assert lines["terceiros"].amount == (base * Decimal("0.058")).quantize(Decimal("0.01"))


def test_simples_annex_iv_has_no_third_parties(snapshot_content, rules):
    view = SnapshotView(snapshot_content)
    a = accepted_assumptions(view, rules)
    taxes = {l.tax for l in charges("SIMPLES", "2026-08", view, a, rules)}
    assert taxes == {"cpp", "rat"}


def test_confirmed_fator_r_profile_brings_payroll_premise(snapshot_content, rules):
    """Perfil alterado pelo usuário para Fator R: a regeneração inclui a folha dos 12 meses."""
    from worker.engine.assumptions import Assumptions

    view = SnapshotView(snapshot_content)
    assert not [s for s in suggest(view, rules) if s.key == "folha.folha_12m"]
    act = view.activities("2026-08")[0]
    confirmed = Assumptions([{"key": "atividade.perfil", "scope": "atividade:" + act.key, "value": {
        "anexo": "V", "presumido": "servicos_gerais", "cumulativo_no_real": False, "fator_r": True}}])
    folha = [s for s in suggest(view, rules, confirmed) if s.key == "folha.folha_12m"]
    assert [s.scope for s in folha] == ["competencia:2026-08"]


def test_activity_key_distinguishes_zero_declared_taxes(snapshot_content):
    """Mesma descrição com e sem ST: premissas de perfil/tributos zerados não podem colidir."""
    import copy

    content = copy.deepcopy(snapshot_content)
    acts = SnapshotView(content).activities("2026-08")
    st = next(a for a in acts if "Com substituição" in a.description)
    other = next(a for a in acts if a is not st)
    for v in content["values"]:
        if v["doc_type"] == "PGDAS_D" and v["competence"] == "2026-08-01" and v["section"] == st.section \
                and v["field_key"] == "receita_informada":
            v["label"] = other.description
    keys = [a.key for a in SnapshotView(content).activities("2026-08")]
    assert len(set(keys)) == 2
    assert sorted("icms" in k.split("~zero-")[1].split("-") for k in keys) == [False, True]
