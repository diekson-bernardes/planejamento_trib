"""Ciclo 6 — atividades mistas e Fator R no planejamento rápido (AT-605–AT-612, AT-614). Caso fictício, sem PDF."""
from decimal import Decimal

import pytest

from conftest import GOLDEN, MISTO_MONTHS, misto_assumptions, misto_content
from worker.engine.decision import project
from worker.engine.fator_r import (MSG_ESCOLHA, TRATAMENTO_KEY, FolhaIncompletaError, build_timeline, folha_12m,
                                   folha_ideal_lines, folha_mes, missing_months)
from worker.engine.quick_view import (PCT_ST, REGIMES, QuickCaseError, build_quick_case, fator_r_adjuster,
                                      rapido_suggestions)
from worker.engine.assumptions import suggest

THRESHOLD = Decimal("0.05")
D = Decimal


def run(content, a, params, rules_2027, decision_params, decision_params_2027):
    qc = build_quick_case(content, a)
    adjust = fator_r_adjuster(qc, qc.assumptions, params)
    res = project(qc.view, qc.assumptions, rules_2027, decision_params_2027, THRESHOLD, base_params=decision_params,
                  regimes=REGIMES, adjust=adjust)
    return qc, res


def fator_r_lines(res):
    seen, out = set(), []
    for l in res.simulation.lines:
        if l.tax == "fator_r" and l.regime == "SIMPLES" and l.period not in seen:
            seen.add(l.period)
            out.append(l)
    return out


# ---------------------------------------------------------------- unidade: folha e janela de 12 meses
def test_folha_includes_fgts_over_salaries(fator_r_params):
    assert folha_mes(D("10000"), D("5000"), fator_r_params) == D("15800.00")     # 10.000 × 1,08 + 5.000


def test_window_and_missing_treatment(fator_r_params):
    informed = {"2026-06": (D("10000"), D("0")), "2026-07": (D("20000"), D("0"))}
    tl = build_timeline(informed, {"2026-06", "2026-07"}, "2026-08",
                        {"2026-06": (D("10000"), D("0")), "2026-07": (D("20000"), D("0")), "2026-09": (D("30000"), D("0"))},
                        fator_r_params)
    assert tl["2026-06"] == D("10800.00") and tl["2026-09"] == D("32400.00")
    assert missing_months(["2026-10"], informed, "2026-08") == [f"2025-{m:02d}" for m in range(10, 13)] + \
        [f"2026-{m:02d}" for m in range(1, 6)] + ["2026-08"]
    with pytest.raises(FolhaIncompletaError, match=MSG_ESCOLHA):                  # AT-608
        folha_12m("2026-10", tl, None)
    zero, o = folha_12m("2026-10", tl, "zero")                                      # AT-609
    assert zero == D("64800.00") and o["meses_sem_folha"] == 9 and o["tratamento"] == "zero"
    media, _ = folha_12m("2026-10", tl, "media")
    assert media == D("64800.00") + D("21600.00") * 9                               # média de 10.800, 21.600 e 32.400


def test_without_any_payroll_only_zero(fator_r_params):
    with pytest.raises(FolhaIncompletaError, match="só é possível considerar zero"):   # AT-610
        folha_12m("2026-10", {}, "media")
    assert folha_12m("2026-10", {}, "zero")[0] == D("0.00")


# ---------------------------------------------------------------- atividades mistas
def test_activities_split_revenue(rules, rules_2027, cnae_table, golden):
    content = misto_content()
    a = misto_assumptions(content, rules, rules_2027, cnae_table, golden)
    qc = build_quick_case(content, a)                                               # AT-606
    assert [x.cnae for x in qc.activities] == ["4744001", "6201501"]
    acts = {x.key: x.receita for x in qc.view.activities("2026-08")}
    com, soft = qc.activities
    assert acts[com.keys["normal"]] == D("106500.00") and acts[soft.keys["normal"]] == D("71000.00")   # 60/40 de 177.500
    assert qc.assumptions.profile(com.keys["normal"]).anexo == "I"
    assert qc.assumptions.profile(soft.keys["normal"]).anexo == "V" and qc.assumptions.profile(soft.keys["normal"]).fator_r


def test_st_and_mono_come_from_commerce_only(rules, rules_2027, cnae_table, golden):
    content = misto_content()
    a = misto_assumptions(content, rules, rules_2027, cnae_table, golden, overrides={(PCT_ST, "caso"): "0.3000"})
    qc = build_quick_case(content, a)                                               # AT-614
    acts = {x.key: x.receita for x in qc.view.activities("2026-08")}
    com, soft = qc.activities
    assert acts[com.keys["st"]] == D("53250.00")                                    # 30% de 177.500 sai do comércio
    assert acts[com.keys["normal"]] == D("53250.00") and acts[soft.keys["st"]] == D("0.00")
    bad = misto_assumptions(content, rules, rules_2027, cnae_table, golden, overrides={(PCT_ST, "caso"): "0.7000"})
    with pytest.raises(QuickCaseError, match="parcela de comércio"):
        build_quick_case(content, bad)


def test_single_activity_gets_all_revenue(rules, rules_2027, cnae_table, golden):
    content = misto_content()
    content["activities"] = [{"cnae": "6201501", "descricao": "Software", "percentual": "100.00"}]   # AT-605
    qc = build_quick_case(content)
    assert sum((x.receita for x in qc.view.activities("2026-08")), D("0")) == D("177500.00")
    content.pop("activities")                                                       # dossiê anterior ao ciclo 6
    qc = build_quick_case(content)
    assert [x.cnae for x in qc.activities] == ["4744001"] and qc.activities[0].percentual == 100


def test_percentages_must_sum_100():
    content = misto_content()
    content["activities"][1]["percentual"] = "39.99"
    with pytest.raises(QuickCaseError, match="somam 99.99%"):
        build_quick_case(content)


def test_unknown_cnae_blocks_simples(rules, rules_2027, cnae_table, golden, fator_r_params, decision_params,
                                     decision_params_2027):
    content = misto_content()
    content["activities"][1]["cnae"] = "0111301"                                  # fora da tabela: sem perfil (AT-612)
    a = misto_assumptions(content, rules, rules_2027, cnae_table, golden)
    qc = build_quick_case(content, a)
    assert qc.assumptions.profile(qc.activities[1].keys["normal"]) is None
    _, res = run(content, a, fator_r_params, rules_2027, decision_params, decision_params_2027)
    assert any("perfil" in p for p in res.simulation.regimes["SIMPLES"].pending)


# ---------------------------------------------------------------- Fator R mês a mês e folha ideal
def test_monthly_fator_r_changes_anexo(rules, rules_2027, cnae_table, golden, fator_r_params, decision_params,
                                       decision_params_2027):
    content = misto_content()
    a = misto_assumptions(content, rules, rules_2027, cnae_table, golden)
    _, res = run(content, a, fator_r_params, rules_2027, decision_params, decision_params_2027)
    lines = fator_r_lines(res)                                                      # AT-607
    assert [l.period for l in lines] == [f"2027-{m:02d}" for m in range(1, 13)]
    # 01/2027: folha 01–08/2026 informada (salários × 1,08 + pró-labore) + 09–12/2026 projetada (média 06–08)
    assert lines[0].base == D("333120.00") + 4 * D("49200.00")
    assert lines[0].rate.quantize(D("0.0001")) == D("0.2585") and "Anexo V" in lines[0].formula
    assert "Anexo III" in lines[3].formula and lines[3].rate >= D("0.28")
    ideal = folha_ideal_lines(res.simulation.lines, res.projected.content, rules_2027, fator_r_params)   # AT-611
    assert {l.period for l in ideal} == {"2027-01", "2027-02", "2027-03"}
    assert all(l.kind == "informativo" and not l.verified for l in ideal)
    jan = {l.tax: l for l in ideal if l.period == "2027-01"}
    assert jan["folha_ideal_economia"].base == ((D("0.28") * D("2050000.00") - lines[0].base) / 12).quantize(D("0.01"))
    assert jan["folha_ideal_prolabore"].amount == (jan["folha_ideal_economia"].base * D("0.11")).quantize(D("0.01"))
    assert set(jan) == {"folha_ideal_economia", "folha_ideal_prolabore", "folha_ideal_salario"}
    assert res.simulation.regimes["SIMPLES"].status == "calculado"


def test_missing_payroll_requires_choice(rules, rules_2027, cnae_table, golden, fator_r_params, decision_params,
                                         decision_params_2027):
    content = misto_content(folha_months=MISTO_MONTHS[-3:])                        # folha só de 06–08/2026
    qc = build_quick_case(content)
    sug = {s.key: s for s in rapido_suggestions(content, qc, suggest(qc.view, rules, None, rules_2027), rules, cnae_table)}
    t = sug[TRATAMENTO_KEY]
    assert t.suggested_value is None and t.choices == ["media", "zero"] and "01/2026" in t.origin["note"]
    assert "folha.folha_12m" not in sug                                              # folha 12m não é sugerida no rápido
    a = misto_assumptions(content, rules, rules_2027, cnae_table, golden)
    with pytest.raises(FolhaIncompletaError, match=MSG_ESCOLHA):                   # AT-608
        run(content, a, fator_r_params, rules_2027, decision_params, decision_params_2027)
    zero = misto_assumptions(content, rules, rules_2027, cnae_table, golden, overrides={(TRATAMENTO_KEY, "caso"): "zero"})
    media = misto_assumptions(content, rules, rules_2027, cnae_table, golden, overrides={(TRATAMENTO_KEY, "caso"): "media"})
    _, rz = run(content, zero, fator_r_params, rules_2027, decision_params, decision_params_2027)
    _, rm = run(content, media, fator_r_params, rules_2027, decision_params, decision_params_2027)
    assert fator_r_lines(rz)[0].base < fator_r_lines(rm)[0].base                   # AT-609


def test_commerce_only_needs_no_payroll_choice(rules, rules_2027, cnae_table, golden):
    content = misto_content(folha_months=MISTO_MONTHS[-1:])
    content["activities"] = [{"cnae": "4744001", "descricao": "Ferragens", "percentual": "100"}]
    qc = build_quick_case(content)
    sug = rapido_suggestions(content, qc, suggest(qc.view, rules, None, rules_2027), rules, cnae_table)
    assert not any(s.key == TRATAMENTO_KEY for s in sug)
    assert fator_r_adjuster(qc, misto_assumptions(content, rules, rules_2027, cnae_table, golden), None) is None



# ---------------------------------------------------------------- golden aprovado (AT-613 para o caso misto)
def test_rapido_misto_2027_matches_approved_golden(rules, rules_2027, cnae_table, golden, fator_r_params,
                                                   decision_params, decision_params_2027):
    g = golden("rapido_misto_2027")
    assert g["approved_by"] and g["approved_at"]
    assert (rules_2027.version, decision_params_2027.version, fator_r_params.version) == (
        g["rules_version"], g["decision_version"], g["fator_r_version"])
    content = misto_content()
    _, res = run(content, misto_assumptions(content, rules, rules_2027, cnae_table, golden), fator_r_params,
                 rules_2027, decision_params, decision_params_2027)
    sim = res.simulation
    assert res.projected.base["receita_anual"] == g["receita_anual"] and sim.ranking == g["ranking"]
    for regime, expected in g["regimes"].items():
        got = sim.regimes[regime]
        assert str(got.total) == expected["total"], regime
        assert {k: str(v) for k, v in sorted(got.by_tax.items())} == expected["by_tax"], regime
        assert {p: str(v) for p, v in sorted(got.by_period.items())} == expected["by_period"], regime
    rec = res.recommendation.as_dict()
    assert {k: rec[k] for k in g["recomendacao"]} == g["recomendacao"]
    rbt = {l.period: l.amount for l in sim.lines if l.tax == "rbt12" and l.regime == "SIMPLES"}
    assert [{"mes": l.period, "folha_12m": str(l.base), "rbt12": str(rbt[l.period]),
             "fator_r": str(l.rate.quantize(D("0.0001"))), "anexo": "III" if l.rate >= D("0.28") else "V"}
            for l in fator_r_lines(res)] == g["fator_r"]
    assert [{"mes": l.period, "tipo": l.tax, "base": str(l.base), "valor": str(l.amount)}
            for l in folha_ideal_lines(sim.lines, res.projected.content, rules_2027, fator_r_params)] == g["folha_ideal"]


# ---------------------------------------------------------------- integração com o Postgres local (sem PDF)
@pytest.mark.db
def test_pipeline_persists_activities_fator_r_and_folha_ideal(db_conn, tenant):
    import json

    from test_decisao_pipeline import ADMIN, as_user
    from worker.pipeline import Pipeline

    content = misto_content()
    with db_conn.transaction():
        db_conn.execute("insert into office_members (office_id, user_id, role) values (%s, %s, 'analyst'), (%s, %s, 'admin')",
                        (tenant.office_id, tenant.user_id, tenant.office_id, ADMIN))
        db_conn.execute("update tax_cases set kind = 'rapido', period_start = '2025-09-01', period_end = '2026-08-31' "
                        "where id = %s", (tenant.case_id,))
    by_doc: dict = {}
    for m in content["manual_values"]:
        by_doc.setdefault((m["doc_type"], m["competence"]), {})[m["field_key"]] = m["value"]
    for (doc, comp), fields in by_doc.items():
        as_user(db_conn, tenant.user_id, "select enter_manual_values(%s, %s, %s, %s::jsonb)",
                (tenant.case_id, doc, comp, json.dumps(fields)))
    as_user(db_conn, tenant.user_id, "select set_company_cnae(%s, '4744001', %s)",
            (tenant.company_id, content["company"]["cnae_descricao"]))
    as_user(db_conn, tenant.user_id, "select set_case_activities(%s, %s::jsonb)",
            (tenant.case_id, json.dumps(content["activities"])))              # AT-602
    snap = as_user(db_conn, tenant.user_id, "select * from homologate_case(%s)", (tenant.case_id,))
    stored = db_conn.execute("select content from snapshots where id = %s", (snap[0]["snapshot_id"],)).fetchone()["content"]
    assert [(a["cnae"], str(a["percentual"])) for a in stored["activities"]] == [("4744001", "60.00"), ("6201501", "40.00")]

    pipe = Pipeline(db_conn, tenant.storage, office_id=tenant.office_id)
    as_user(db_conn, tenant.user_id, "select request_planning(%s)", (tenant.case_id,))
    pipe.drain()
    rows = db_conn.execute("select id, key, scope, suggested_value from assumptions where case_id = %s and status = 'pending'",
                           (tenant.case_id,)).fetchall()
    keys = {r["key"] for r in rows}
    assert "folha.folha_12m" not in keys and "rapido.folha_incompleta" not in keys   # folha completa: nada a escolher
    values = {"reforma.cbs_aliquota": "0.095", "reforma.ibs_aliquota": "0.001", "reforma.crescimento": "0.05",
              "reforma.creditos_base": "30000.00"}
    decl = GOLDEN / "motor_202606_08.json"
    values.update(json.loads(decl.read_text(encoding="utf-8"))["assumption_overrides"])
    for r in rows:
        as_user(db_conn, tenant.user_id, "select confirm_assumption(%s, %s::jsonb, %s)",
                (r["id"], json.dumps(values.get(r["key"], r["suggested_value"])), "teste do ciclo 6"))
    as_user(db_conn, tenant.user_id, "select request_projection(%s, 2027)", (tenant.case_id,))
    pipe.drain()
    proj = db_conn.execute("select * from projections where case_id = %s order by created_at desc limit 1",
                           (tenant.case_id,)).fetchone()
    assert proj["status"] == "done", proj["error_message"]
    lines = db_conn.execute("select period, tax, kind, base, rate, amount from projection_lines where projection_id = %s "
                            "and regime = 'SIMPLES' and tax in ('fator_r', 'folha_ideal_prolabore') order by period, tax",
                            (proj["id"],)).fetchall()
    fr = {l["period"]: l for l in lines if l["tax"] == "fator_r"}
    assert fr["2027-01"]["base"] == D("529920.00") and fr["2027-04"]["rate"] >= D("0.28")
    ideal = [l for l in lines if l["tax"] == "folha_ideal_prolabore"]
    assert [l["period"] for l in ideal] == ["2027-01", "2027-02", "2027-03"] and all(l["kind"] == "informativo" for l in ideal)

    # AT-616: o PDF da recomendação traz atividades, Fator R mês a mês e folha ideal
    import io

    import pdfplumber

    from test_decisao_pipeline import recommendation

    as_user(db_conn, ADMIN, "select set_technical_responsible(%s, %s, true, 'Contadora Fictícia', 'SP-000000/O-0')",
            (tenant.office_id, ADMIN))
    rec = recommendation(db_conn, tenant)
    as_user(db_conn, tenant.user_id, "select submit_recommendation(%s)", (rec["id"],))
    as_user(db_conn, ADMIN, "select approve_recommendation(%s)", (rec["id"],))
    as_user(db_conn, tenant.user_id, "select request_report(%s)", (rec["id"],))
    pipe.drain()
    rec = recommendation(db_conn, tenant)
    assert rec["status"] == "emitida"
    text = "\n".join(p.extract_text() or "" for p in pdfplumber.open(io.BytesIO(tenant.storage.objects[rec["pdf_path"]])).pages)
    for expected in ("Atividades da empresa", "6201-5/01", "40,00%", "Fator R mês a mês", "25,85%",
                     "Folha ideal para o Anexo III", "3.426,87"):
        assert expected in text, expected
