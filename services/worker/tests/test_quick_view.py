"""Ciclo 5 — planejamento rápido: snapshot sintético, sugestões, três alternativas, faixa do Simples e bloqueios
(AT-505, AT-510–AT-515)."""
import copy
from decimal import Decimal

import pytest

from conftest import rapido_assumptions
from worker.engine.assumptions import suggest
from worker.engine.calculate import NAO_CALCULADO
from worker.engine.decision import project
from worker.engine.quick_view import (PCT_MONO, PCT_ST, REGIMES, QuickCaseError, build_quick_case,
                                      rapido_suggestions)

pytestmark = pytest.mark.samples
THRESHOLD = Decimal("0.05")


def run(content, a, rules_2027, decision_params, decision_params_2027):
    qc = build_quick_case(content, a)
    return project(qc.view, qc.assumptions, rules_2027, decision_params_2027, THRESHOLD, base_params=decision_params,
                   regimes=REGIMES)


def test_synthetic_view_uses_declaration_and_pdfs(rapido_content):
    qc = build_quick_case(rapido_content)
    assert qc.realized == ["2026-06", "2026-07", "2026-08"]
    assert qc.view.complete_competences() == qc.realized
    assert qc.view.value("PGDAS_D", "2026-06", "receita.rpa", "total") == Decimal("321353.79")
    # RBT12 de 08/2026 = 08/2025 (média, antes da declaração) + 09/2025–07/2026 declarados
    assert "2025-08" in qc.estimated_prior and "2025-09" not in qc.estimated_prior
    folha = qc.view.value("FOLHA_ALTERDATA", "2026-08", "aux.base_empregados")
    assert folha is not None and folha > 0                                   # folha em PDF copiada


def test_suggestions_for_rapido(rapido_content, rules, rules_2027, cnae_table):
    qc = build_quick_case(rapido_content)
    sug = rapido_suggestions(rapido_content, qc, suggest(qc.view, rules, None, rules_2027), rules, cnae_table)
    by = {(s.key, s.scope): s for s in sug}
    perfil = by[("atividade.perfil", "atividade:" + qc.activity_keys["normal"])]
    assert perfil.suggested_value["anexo"] == "I" and perfil.origin["cnae"] == "4744001"      # AT-510
    assert not any(s.key.startswith("real.") or s.key == "pis_cofins_creditos_base" for s in sug)
    assert not any(qc.activity_keys["st"] in s.scope or qc.activity_keys["mono"] in s.scope for s in sug)
    assert by[(PCT_ST, "caso")].suggested_value == "0.0000" and by[(PCT_MONO, "caso")].suggested_value == "0.0000"
    assert all(by[("reforma.creditos_base", "competencia:" + c)].suggested_value is None for c in qc.realized)
    icms = by[("icms_regime_normal", "competencia:2026-08")]
    assert Decimal(icms.suggested_value) > 0 and icms.origin["source"] == "proxy_das"


def test_unknown_cnae_leaves_profile_without_suggestion(rapido_content, rules, rules_2027, cnae_table):
    content = copy.deepcopy(rapido_content)
    content["company"]["cnae_principal"] = "0111301"
    qc = build_quick_case(content)
    sug = rapido_suggestions(content, qc, suggest(qc.view, rules, None, rules_2027), rules, cnae_table)
    perfil = next(s for s in sug if s.key == "atividade.perfil")
    assert perfil.suggested_value is None                                      # AT-511


def test_three_alternatives_with_band(rapido_content, rules, rules_2027, cnae_table, golden, rapido_credits,
                                      decision_params, decision_params_2027):
    a = rapido_assumptions(rapido_content, rules, rules_2027, cnae_table, golden, rapido_credits)
    res = run(rapido_content, a, rules_2027, decision_params, decision_params_2027)
    sim = res.simulation
    assert set(sim.regimes) == set(REGIMES) and "REAL" not in sim.eligibility                  # AT-512
    assert all(r.status == "calculado" for r in sim.regimes.values())
    assert not any(l.regime == "REAL" for l in sim.lines)
    faixas = [l for l in sim.lines if l.tax == "faixa" and l.regime == "SIMPLES"]            # AT-513
    assert sorted({l.period for l in faixas}) == [f"2027-{m:02d}" for m in range(1, 13)]
    o = faixas[0].origin
    assert o["anexo"] == "I" and o["faixa"] in (5, 6) and Decimal(o["efetiva"]) > 0
    assert all(l.amount == 0 for l in faixas)                                                 # fora dos totais
    assert res.projected.base["crescimento"] == "0.05" and res.projected.year == 2027


def test_percentages_split_activities(rapido_content, rules, rules_2027, cnae_table, golden, rapido_credits):
    a = rapido_assumptions(rapido_content, rules, rules_2027, cnae_table, golden, rapido_credits,
                           overrides={(PCT_ST, "caso"): "0.3000", (PCT_MONO, "caso"): "0.1000"})
    qc = build_quick_case(rapido_content, a)
    acts = {x.key: x.receita for x in qc.view.activities("2026-08")}
    total = Decimal("203180.77")
    assert acts[qc.activity_keys["st"]] == (total * Decimal("0.3")).quantize(Decimal("0.01"))
    assert acts[qc.activity_keys["mono"]] == (total * Decimal("0.1")).quantize(Decimal("0.01"))
    assert qc.assumptions.zeroed(qc.activity_keys["st"]) == {"icms"}
    assert qc.assumptions.profile(qc.activity_keys["mono"]).anexo == "I"
    bad = rapido_assumptions(rapido_content, rules, rules_2027, cnae_table, golden, rapido_credits,
                             overrides={(PCT_ST, "caso"): "0.8000", (PCT_MONO, "caso"): "0.3000"})
    with pytest.raises(QuickCaseError, match="percentuais"):
        build_quick_case(rapido_content, bad)


def test_manual_values_make_a_realized_month(rapido_content, rules, rules_2027, cnae_table):
    content = copy.deepcopy(rapido_content)
    content["manual_values"] = [
        {"doc_type": "FOLHA", "competence": "2026-05-01", "field_key": "folha.salarios", "value": "40000.00"},
        {"doc_type": "FOLHA", "competence": "2026-05-01", "field_key": "folha.pro_labore", "value": "5000.00"},
        {"doc_type": "DRE", "competence": "2026-05-01", "field_key": "dre.resultado", "value": "30000.00"},
        {"doc_type": "DRE", "competence": "2026-05-01", "field_key": "dre.outras_receitas", "value": "1234.56"},
    ]
    qc = build_quick_case(content)
    assert qc.realized[0] == "2026-05"                                                     # AT-505
    assert qc.view.value("FOLHA_ALTERDATA", "2026-05", "aux.base_empregados") == Decimal("40000.00")
    assert qc.view.value("FOLHA_ALTERDATA", "2026-05", "auxiliares.base_socios") == Decimal("5000.00")
    sug = rapido_suggestions(content, qc, suggest(qc.view, rules, None, rules_2027), rules, cnae_table)
    outras = next(s for s in sug if (s.key, s.scope) == ("outras_receitas", "competencia:2026-05"))
    assert outras.suggested_value == "1234.56" and outras.origin["source"] == "manual"


def test_revenue_above_limit_makes_simples_ineligible(rapido_content, rules, rules_2027, cnae_table, golden,
                                                      rapido_credits, decision_params, decision_params_2027):
    content = copy.deepcopy(rapido_content)
    for v in content["values"]:
        if v["doc_type"] == "DECLARACAO_FATURAMENTO":
            v["value"] = str(Decimal(str(v["value"])) * Decimal("1.5"))
    a = rapido_assumptions(content, rules, rules_2027, cnae_table, golden, rapido_credits)
    res = run(content, a, rules_2027, decision_params, decision_params_2027)
    sim = res.simulation
    # AT-514: Simples por dentro e por fora saem do comparativo (RBT12 acima da última faixa) com alerta de teto;
    # a recomendação fica entre as alternativas restantes
    for regime in ("SIMPLES", "SIMPLES_HIBRIDO"):
        assert sim.regimes[regime].status == NAO_CALCULADO
        assert any("acima da última faixa" in p for p in sim.regimes[regime].pending)
        assert any("acima do teto" in r["motivo"] for r in sim.eligibility[regime].as_dict()["reasons"])
    assert sim.ranking == ["PRESUMIDO"] and res.recommendation.as_dict()["regime"] == "PRESUMIDO"


def test_pending_profile_blocks(rapido_content, rules, rules_2027, cnae_table, golden, rapido_credits,
                                decision_params, decision_params_2027):
    qc = build_quick_case(rapido_content)
    key = qc.activity_keys["normal"]
    a = rapido_assumptions(rapido_content, rules, rules_2027, cnae_table, golden, rapido_credits,
                           overrides={("atividade.perfil", "atividade:" + key): None})
    res = run(rapido_content, a, rules_2027, decision_params, decision_params_2027)
    assert res.simulation.regimes["SIMPLES"].status == NAO_CALCULADO
    assert any("perfil" in p for p in res.simulation.regimes["SIMPLES"].pending)


def test_requires_month_with_folha_and_dre(rapido_content):
    content = copy.deepcopy(rapido_content)
    content["values"] = [v for v in content["values"] if v["doc_type"] != "DRE_ALTERDATA"]
    with pytest.raises(QuickCaseError, match="folha e DRE"):
        build_quick_case(content)
