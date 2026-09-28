"""Integração com o Postgres local — ciclo 5 (planejamento rápido): AT-504 a AT-509, AT-512, AT-516, AT-517.

Fluxo real: Declaração de Faturamento + folha/DRE em PDF + mês digitado → CNAE (automação simulada) → homologação →
premissas → Projetar 2027 (3 alternativas) → aprovação do responsável técnico → PDF "planejamento rápido"."""
import hashlib
import io
import json
import time

import pdfplumber
import psycopg
import pytest

from conftest import RAPIDO_NAMES, REFORM_GOLDEN
from test_decisao_pipeline import ADMIN, as_user, recommendation
from worker import pipeline as pipeline_module
from worker.pipeline import Pipeline

pytestmark = [pytest.mark.db, pytest.mark.samples]
LIMIT_SECONDS = 60
MANUAL_MONTH = "2026-05-01"


def make_rapido(db_conn, tenant):
    with db_conn.transaction():
        db_conn.execute("insert into office_members (office_id, user_id, role) values (%s, %s, 'analyst'), (%s, %s, 'admin')",
                        (tenant.office_id, tenant.user_id, tenant.office_id, ADMIN))
        db_conn.execute("update tax_cases set kind = 'rapido', period_start = '2025-09-01', period_end = '2026-08-31' "
                        "where id = %s", (tenant.case_id,))


def fake_lookup(url, cnpj, timeout=20.0, transport=None):
    return {"razao_social": "EMPRESA TESTE", "cnae_principal": "4744001",
            "cnae_descricao": "Comércio varejista de ferragens e ferramentas",
            "cnaes_secundarios": [{"codigo": "4742300", "descricao": "Comércio varejista de material elétrico"}]}


def confirm_rapido(db_conn, tenant, golden, credits):
    decl = golden("motor_202606_08")["assumption_overrides"]
    rows = db_conn.execute("select id, key, scope, suggested_value from assumptions where case_id = %s "
                           "and status = 'pending'", (tenant.case_id,)).fetchall()
    for r in rows:
        month = r["scope"].removeprefix("competencia:")
        if r["key"] in decl:
            value, reason = decl[r["key"]], "Declaração do cliente em teste"
        elif r["key"] in REFORM_GOLDEN:
            value, reason = REFORM_GOLDEN[r["key"]], "Premissa da Reforma informada no teste"
        elif r["key"] == "reforma.creditos_base":
            value, reason = credits.get(month, "100000.00"), "Compras creditáveis informadas no teste"
        else:
            value, reason = r["suggested_value"], None
        as_user(db_conn, tenant.user_id, "select confirm_assumption(%s, %s::jsonb, %s)", (r["id"], json.dumps(value), reason))


def test_rapido_flow(db_conn, tenant, sample, golden, rapido_credits, monkeypatch):
    make_rapido(db_conn, tenant)
    for name in RAPIDO_NAMES:
        tenant.add_file(sample(name), name + ".pdf")
    pipe = Pipeline(db_conn, tenant.storage, office_id=tenant.office_id)
    pipe.drain()
    assert db_conn.execute("select count(*) as n from reconciliations where case_id = %s",
                           (tenant.case_id,)).fetchone()["n"] == 0                 # sem R1–R7 no rápido

    # AT-505: mês sem PDF digitado; AT-506: mês com PDF recusa digitação
    as_user(db_conn, tenant.user_id, "select enter_manual_values(%s, 'FOLHA', %s, %s::jsonb)",
            (tenant.case_id, MANUAL_MONTH, json.dumps({"folha.salarios": "40000.00", "folha.pro_labore": "5000.00"})))
    as_user(db_conn, tenant.user_id, "select enter_manual_values(%s, 'DRE', %s, %s::jsonb)",
            (tenant.case_id, MANUAL_MONTH, json.dumps({"dre.resultado": "30000.00", "dre.outras_receitas": "1234.56"})))
    with pytest.raises(psycopg.errors.RaiseException, match="ajuste justificado"):
        as_user(db_conn, tenant.user_id, "select enter_manual_values(%s, 'FOLHA', '2026-08-01', %s::jsonb)",
                (tenant.case_id, json.dumps({"folha.salarios": "1.00"})))
    entered = db_conn.execute("select entered_by from manual_values where case_id = %s limit 1", (tenant.case_id,)).fetchone()
    assert str(entered["entered_by"]) == tenant.user_id

    # sem CNAE a homologação bloqueia; AT-508: consulta pela automação (simulada) grava só CNAE
    with pytest.raises(psycopg.errors.RaiseException, match="CNAE principal"):
        as_user(db_conn, tenant.user_id, "select * from homologate_case(%s)", (tenant.case_id,))
    monkeypatch.setenv("CNPJ_LOOKUP_MCP_URL", "https://mcp.example.test/mcp")
    monkeypatch.setattr(pipeline_module, "consultar_cnpj", fake_lookup)
    as_user(db_conn, tenant.user_id, "select request_company_lookup(%s)", (tenant.company_id,))
    pipe.drain()
    co = db_conn.execute("select legal_name, cnae_principal, cnae_origem, cnae_consulta_status, cnaes_secundarios "
                         "from companies where id = %s", (tenant.company_id,)).fetchone()
    assert (co["cnae_principal"], co["cnae_origem"], co["cnae_consulta_status"]) == ("4744001", "receita", "ok")
    assert co["legal_name"] == "Empresa teste" and co["cnaes_secundarios"][0]["codigo"] == "4742300"

    snap = as_user(db_conn, tenant.user_id, "select * from homologate_case(%s)", (tenant.case_id,))
    content = db_conn.execute("select content from snapshots where id = %s", (snap[0]["snapshot_id"],)).fetchone()["content"]
    assert content["case"]["kind"] == "rapido" and content["company"]["cnae_principal"] == "4744001"
    assert {m["field_key"] for m in content["manual_values"]} == {"folha.salarios", "folha.pro_labore",
                                                                  "dre.resultado", "dre.outras_receitas"}

    as_user(db_conn, tenant.user_id, "select request_planning(%s)", (tenant.case_id,))
    pipe.drain()
    keys = {r["key"] for r in db_conn.execute("select key from assumptions where case_id = %s", (tenant.case_id,)).fetchall()}
    assert "rapido.pct_icms_st" in keys and not any(k.startswith("real.") for k in keys)
    confirm_rapido(db_conn, tenant, golden, rapido_credits)

    with pytest.raises(psycopg.errors.RaiseException, match="só 2027"):
        as_user(db_conn, tenant.user_id, "select request_calculation(%s)", (tenant.case_id,))
    with pytest.raises(psycopg.errors.RaiseException, match="projeta só 2027"):
        as_user(db_conn, tenant.user_id, "select request_projection(%s, 2026)", (tenant.case_id,))

    as_user(db_conn, ADMIN, "select set_technical_responsible(%s, %s, true, 'Maria Contadora', 'SP-123456/O-7')",
            (tenant.office_id, ADMIN))
    started = time.monotonic()
    as_user(db_conn, tenant.user_id, "select request_projection(%s, 2027)", (tenant.case_id,))
    pipe.drain()
    elapsed = time.monotonic() - started
    assert elapsed <= LIMIT_SECONDS, f"{elapsed:.1f}s"                                    # AT-516
    proj = db_conn.execute("select * from projections where case_id = %s order by created_at desc limit 1",
                           (tenant.case_id,)).fetchone()
    assert proj["status"] == "done" and proj["year"] == 2027
    regimes = {r["regime"] for r in db_conn.execute("select distinct regime from projection_lines where projection_id = %s",
                                                    (proj["id"],)).fetchall()}
    assert regimes == {"SIMPLES", "SIMPLES_HIBRIDO", "PRESUMIDO"}                         # AT-512
    print(f"\n[ciclo 5] projeção rápida 2027 em {elapsed:.2f}s ({proj['duration_ms']} ms, {proj['engine_runs']} execuções)")

    rec = recommendation(db_conn, tenant)
    assert rec["computed_status"] in ("recomendado", "inconclusivo")
    as_user(db_conn, tenant.user_id, "select submit_recommendation(%s)", (rec["id"],))
    as_user(db_conn, ADMIN, "select approve_recommendation(%s)", (rec["id"],))
    as_user(db_conn, tenant.user_id, "select request_report(%s)", (rec["id"],))
    pipe.drain()
    rec = recommendation(db_conn, tenant)
    assert rec["status"] == "emitida"
    pdf = tenant.storage.objects[rec["pdf_path"]]
    assert hashlib.sha256(pdf).hexdigest() == rec["pdf_sha256"].strip()
    text = "\n".join(p.extract_text() or "" for p in pdfplumber.open(io.BytesIO(pdf)).pages)
    for expected in ("Planejamento tributário rápido", "4744-0/01", "Faixa do Simples", "digitado", "híbrido"):
        assert expected in text, expected                                                 # AT-517
    assert "Resultado: Lucro Real" not in text                                          # sem Real no rápido


def test_lookup_failure_allows_typed_cnae(db_conn, tenant, monkeypatch):
    make_rapido(db_conn, tenant)
    monkeypatch.setenv("CNPJ_LOOKUP_MCP_URL", "")
    as_user(db_conn, tenant.user_id, "select request_company_lookup(%s)", (tenant.company_id,))
    Pipeline(db_conn, tenant.storage, office_id=tenant.office_id).drain()
    co = db_conn.execute("select cnae_consulta_status, cnae_consulta_erro from companies where id = %s",
                         (tenant.company_id,)).fetchone()
    assert co["cnae_consulta_status"] == "falhou" and "informe o CNAE" in co["cnae_consulta_erro"]   # AT-509
    as_user(db_conn, tenant.user_id, "select set_company_cnae(%s, '4744-0/01', 'Ferragens')", (tenant.company_id,))
    co = db_conn.execute("select cnae_principal, cnae_origem from companies where id = %s", (tenant.company_id,)).fetchone()
    assert (co["cnae_principal"], co["cnae_origem"]) == ("4744001", "manual")


def test_rapido_without_revenue_or_folha_is_blocked(db_conn, tenant, sample):
    make_rapido(db_conn, tenant)
    as_user(db_conn, tenant.user_id, "select set_company_cnae(%s, '4744001', null)", (tenant.company_id,))
    tenant.add_file(sample("dre_202608"), "dre.pdf")
    Pipeline(db_conn, tenant.storage, office_id=tenant.office_id).drain()
    with pytest.raises(psycopg.errors.RaiseException) as exc:
        as_user(db_conn, tenant.user_id, "select * from homologate_case(%s)", (tenant.case_id,))
    msg = str(exc.value)
    assert "Faturamento ausente: 09/2025" in msg and "08/2026" in msg                     # AT-504
    assert "folha de ao menos um mês" in msg                                              # AT-507
