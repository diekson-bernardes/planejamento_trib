"""Integração com o Postgres local — gestão do dossiê (pós-ciclo 5): razão social pela consulta do CNPJ, reabrir
dossiê homologado com PDF emitido, excluir arquivo, editar dossiê, excluir dossiê e empresa (qualquer membro, com
motivo e auditoria; Storage limpo pelo job purge_storage)."""
import json

import psycopg
import pytest

from conftest import RAPIDO_NAMES
from test_decisao_pipeline import ADMIN, as_user, recommendation
from test_rapido_pipeline import confirm_rapido, fake_lookup, make_rapido
from worker import pipeline as pipeline_module
from worker.pipeline import Pipeline

pytestmark = [pytest.mark.db, pytest.mark.samples]


def count(db_conn, table, case_id):
    return db_conn.execute(f"select count(*) as n from {table} where case_id = %s", (case_id,)).fetchone()["n"]


def audit(db_conn, office_id, event):
    return db_conn.execute("select before, after, actor from audit_events where office_id = %s and event = %s "
                           "order by id desc limit 1", (office_id, event)).fetchone()


def emitted_case(db_conn, tenant, sample, golden, rapido_credits):
    """Dossiê rápido homologado com recomendação aprovada e PDF emitido."""
    make_rapido(db_conn, tenant)
    for name in RAPIDO_NAMES:
        tenant.add_file(sample(name), name + ".pdf")
    pipe = Pipeline(db_conn, tenant.storage, office_id=tenant.office_id)
    pipe.drain()
    as_user(db_conn, tenant.user_id, "select set_company_cnae(%s, '4744001', null)", (tenant.company_id,))
    as_user(db_conn, tenant.user_id, "select * from homologate_case(%s)", (tenant.case_id,))
    as_user(db_conn, tenant.user_id, "select request_planning(%s)", (tenant.case_id,))
    pipe.drain()
    confirm_rapido(db_conn, tenant, golden, rapido_credits)
    as_user(db_conn, ADMIN, "select set_technical_responsible(%s, %s, true, 'Maria Contadora', 'SP-123456/O-7')",
            (tenant.office_id, ADMIN))
    as_user(db_conn, tenant.user_id, "select request_projection(%s, 2027)", (tenant.case_id,))
    pipe.drain()
    rec = recommendation(db_conn, tenant)
    as_user(db_conn, tenant.user_id, "select submit_recommendation(%s)", (rec["id"],))
    as_user(db_conn, ADMIN, "select approve_recommendation(%s)", (rec["id"],))
    as_user(db_conn, tenant.user_id, "select request_report(%s)", (rec["id"],))
    pipe.drain()
    rec = recommendation(db_conn, tenant)
    assert rec["status"] == "emitida" and rec["pdf_path"] in tenant.storage.objects
    return pipe, rec


def test_reopen_edit_delete_case_and_company(db_conn, tenant, sample, golden, rapido_credits):
    pipe, rec = emitted_case(db_conn, tenant, sample, golden, rapido_credits)
    report_path = rec["pdf_path"]

    # reabrir: motivo obrigatório; snapshot, projeções, recomendações e PDF emitido saem; premissas ficam
    with pytest.raises(psycopg.errors.RaiseException, match="motivo"):
        as_user(db_conn, tenant.user_id, "select reopen_case(%s, 'x')", (tenant.case_id,))
    assumptions_before = count(db_conn, "assumptions", tenant.case_id)
    as_user(db_conn, tenant.user_id, "select reopen_case(%s, 'Folha de agosto corrigida pelo cliente')", (tenant.case_id,))
    pipe.drain()
    status = db_conn.execute("select status from tax_cases where id = %s", (tenant.case_id,)).fetchone()["status"]
    assert status == "review"
    for table in ("snapshots", "projections", "recommendations", "simulations"):
        assert count(db_conn, table, tenant.case_id) == 0, table
    assert count(db_conn, "assumptions", tenant.case_id) == assumptions_before
    assert report_path not in tenant.storage.objects                           # PDF emitido removido do Storage
    ev = audit(db_conn, tenant.office_id, "case.reopened")
    assert ev["after"]["reason"] == "Folha de agosto corrigida pelo cliente" and ev["before"]["snapshot_sha256"]
    assert str(ev["actor"]) == tenant.user_id

    # excluir arquivo (reaberto: permitido); objeto do Storage removido
    dre = db_conn.execute("select id, storage_path from source_files where case_id = %s and original_name = 'dre_202608.pdf'",
                          (tenant.case_id,)).fetchone()
    as_user(db_conn, tenant.user_id, "select delete_source_file(%s)", (dre["id"],))
    pipe.drain()
    assert db_conn.execute("select count(*) as n from source_files where id = %s", (dre["id"],)).fetchone()["n"] == 0
    assert db_conn.execute("select count(*) as n from extracted_values where file_id = %s", (dre["id"],)).fetchone()["n"] == 0
    assert dre["storage_path"] not in tenant.storage.objects
    assert audit(db_conn, tenant.office_id, "file.deleted")["before"]["original_name"] == "dre_202608.pdf"

    # editar: rápido exige 12 meses; completo aceita outro período e descarta valores digitados
    as_user(db_conn, tenant.user_id, "select enter_manual_values(%s, 'FOLHA', '2026-05-01', %s::jsonb)",
            (tenant.case_id, json.dumps({"folha.salarios": "1000.00"})))
    with pytest.raises(psycopg.errors.RaiseException, match="12 meses"):
        as_user(db_conn, tenant.user_id, "select update_case(%s, '2026-01-01', '2026-08-31', 'rapido')", (tenant.case_id,))
    as_user(db_conn, tenant.user_id, "select update_case(%s, '2026-06-01', '2026-08-31', 'completo')", (tenant.case_id,))
    row = db_conn.execute("select kind, period_start::text, period_end::text from tax_cases where id = %s",
                          (tenant.case_id,)).fetchone()
    assert (row["kind"], row["period_start"], row["period_end"]) == ("completo", "2026-06-01", "2026-08-31")
    assert count(db_conn, "manual_values", tenant.case_id) == 0

    # excluir a empresa com dossiê: recusado
    with pytest.raises(psycopg.errors.RaiseException, match="tem dossiês"):
        as_user(db_conn, tenant.user_id, "select delete_company(%s)", (tenant.company_id,))

    # excluir o dossiê: tudo sai do banco e do Storage; auditoria registra o motivo
    as_user(db_conn, tenant.user_id, "select delete_case(%s, 'Dossiê criado em duplicidade')", (tenant.case_id,))
    pipe.drain()
    assert db_conn.execute("select count(*) as n from tax_cases where id = %s", (tenant.case_id,)).fetchone()["n"] == 0
    for table in ("source_files", "extracted_values", "assumptions", "manual_values", "reconciliations"):
        assert count(db_conn, table, tenant.case_id) == 0, table
    assert not [p for p in tenant.storage.objects if p.startswith(f"{tenant.office_id}/{tenant.case_id}/")]
    ev = audit(db_conn, tenant.office_id, "case.deleted")
    assert ev["after"]["reason"] == "Dossiê criado em duplicidade" and ev["before"]["files"] == len(RAPIDO_NAMES) - 1

    # sem dossiês, a empresa pode ser excluída
    as_user(db_conn, tenant.user_id, "select delete_company(%s)", (tenant.company_id,))
    assert db_conn.execute("select count(*) as n from companies where id = %s", (tenant.company_id,)).fetchone()["n"] == 0


def test_delete_homologated_case_with_emitted_pdf(db_conn, tenant, sample, golden, rapido_credits):
    """Qualquer membro exclui direto um dossiê homologado com PDF emitido (decisão do usuário)."""
    pipe, rec = emitted_case(db_conn, tenant, sample, golden, rapido_credits)
    as_user(db_conn, tenant.user_id, "select delete_case(%s, 'Planejamento substituído por outro')", (tenant.case_id,))
    pipe.drain()
    assert db_conn.execute("select count(*) as n from tax_cases where id = %s", (tenant.case_id,)).fetchone()["n"] == 0
    assert db_conn.execute("select count(*) as n from recommendation_events where recommendation_id = %s",
                           (rec["id"],)).fetchone()["n"] == 0
    assert rec["pdf_path"] not in tenant.storage.objects
    assert audit(db_conn, tenant.office_id, "case.deleted")["before"]["status"] == "homologated"


def test_legal_name_comes_from_cnpj_lookup(db_conn, tenant, monkeypatch):
    """Empresa cadastrada só com o CNPJ: a consulta preenche a razão social; a digitada nunca é sobrescrita."""
    make_rapido(db_conn, tenant)
    with db_conn.transaction():
        db_conn.execute("update companies set legal_name = 'CNPJ 37.704.456/0001-42', razao_social_pendente = true "
                        "where id = %s", (tenant.company_id,))
    with pytest.raises(psycopg.errors.RaiseException, match="Razão social da empresa pendente"):
        as_user(db_conn, tenant.user_id, "select * from homologate_case(%s)", (tenant.case_id,))
    monkeypatch.setenv("CNPJ_LOOKUP_MCP_URL", "https://mcp.example.test/mcp")
    monkeypatch.setattr(pipeline_module, "consultar_cnpj", fake_lookup)
    as_user(db_conn, tenant.user_id, "select request_company_lookup(%s)", (tenant.company_id,))
    Pipeline(db_conn, tenant.storage, office_id=tenant.office_id).drain()
    co = db_conn.execute("select legal_name, razao_social_pendente, cnae_principal from companies where id = %s",
                         (tenant.company_id,)).fetchone()
    assert (co["legal_name"], co["razao_social_pendente"], co["cnae_principal"]) == ("EMPRESA TESTE", False, "4744001")

    as_user(db_conn, tenant.user_id, "select update_company(%s, 'Nome Digitado Ltda')", (tenant.company_id,))
    as_user(db_conn, tenant.user_id, "select request_company_lookup(%s)", (tenant.company_id,))
    Pipeline(db_conn, tenant.storage, office_id=tenant.office_id).drain()
    assert db_conn.execute("select legal_name from companies where id = %s",
                           (tenant.company_id,)).fetchone()["legal_name"] == "Nome Digitado Ltda"
