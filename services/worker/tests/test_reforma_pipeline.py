"""Integração com o Postgres local — ciclo 4 (Reforma 2027).

Fluxo real: 12 PDFs + Livro de Apuração → R7 → homologação → premissas (2026 confirmadas; 2027 pendentes não bloqueiam
2026) → projeção 2027 bloqueada sem alíquotas → alíquotas/crescimento confirmados → projeção 2027 com 4 alternativas
→ aprovação → PDF emitido."""
import hashlib
import json
import time

import pytest

from conftest import REFORM_GOLDEN, TenantFixture
from test_decisao_pipeline import ADMIN, as_user, confirm_all, prepare, recommendation
from worker.pipeline import Pipeline

pytestmark = [pytest.mark.db, pytest.mark.samples]
LIMIT_SECONDS = 60


def latest_projection(db_conn, tenant):
    return db_conn.execute("select * from projections where case_id = %s order by created_at desc limit 1",
                           (tenant.case_id,)).fetchone()


def confirm_reform(db_conn, tenant):
    rows = db_conn.execute("select id, key, suggested_value from assumptions where case_id = %s "
                           "and grp = 'reforma_2027' and status = 'pending'", (tenant.case_id,)).fetchall()
    for r in rows:
        value = REFORM_GOLDEN.get(r["key"], r["suggested_value"])
        reason = "Premissa da Reforma informada no teste" if r["key"] in REFORM_GOLDEN else None
        as_user(db_conn, tenant.user_id, "select confirm_assumption(%s, %s::jsonb, %s)", (r["id"], json.dumps(value), reason))


def test_reform_2027_flow(db_conn, tenant, sample, golden):
    pipe = prepare(db_conn, tenant, sample)

    r7 = db_conn.execute("select status, left_value, right_value from reconciliations "
                         "where case_id = %s and rule = 'R7'", (tenant.case_id,)).fetchall()
    assert [(r["status"], str(r["left_value"])) for r in r7] == [("ok", "149985.71")]

    groups = {r["key"]: r["status"] for r in db_conn.execute(
        "select key, status from assumptions where case_id = %s and grp = 'reforma_2027'", (tenant.case_id,)).fetchall()}
    assert {"reforma.cbs_aliquota", "reforma.ibs_aliquota", "reforma.crescimento", "reforma.creditos_base"} <= set(groups)

    confirm_all(db_conn, tenant, golden)                       # só 2026: o grupo reforma_2027 continua pendente
    as_user(db_conn, tenant.user_id, "select request_calculation(%s)", (tenant.case_id,))   # 2026 não bloqueia
    as_user(db_conn, tenant.user_id, "select request_projection(%s, 2027)", (tenant.case_id,))
    pipe.drain()
    blocked = latest_projection(db_conn, tenant)
    assert blocked["year"] == 2027 and blocked["recommendation"]["status"] == "bloqueado"

    confirm_reform(db_conn, tenant)
    as_user(db_conn, ADMIN, "select set_technical_responsible(%s, %s, true, 'Maria Contadora', 'SP-123456/O-7')",
            (tenant.office_id, ADMIN))
    started = time.monotonic()
    as_user(db_conn, tenant.user_id, "select request_projection(%s, 2027)", (tenant.case_id,))
    pipe.drain()
    elapsed = time.monotonic() - started
    assert elapsed <= LIMIT_SECONDS, f"{elapsed:.1f}s"
    proj = latest_projection(db_conn, tenant)
    assert proj["status"] == "done" and proj["year"] == 2027 and proj["rules_version"] == "2027.1.0"
    regimes = {r["regime"] for r in db_conn.execute(
        "select distinct regime from projection_lines where projection_id = %s", (proj["id"],)).fetchall()}
    assert regimes == {"SIMPLES", "PRESUMIDO", "REAL", "SIMPLES_HIBRIDO"}
    taxes = {r["tax"] for r in db_conn.execute(
        "select distinct tax from projection_lines where projection_id = %s", (proj["id"],)).fetchall()}
    assert {"cbs", "ibs"} <= taxes and not taxes & {"pis", "cofins", "ipi"}
    print(f"\n[ciclo 4] projeção 2027 em {elapsed:.2f}s ({proj['duration_ms']} ms no worker, {proj['engine_runs']} execuções)")

    rec = recommendation(db_conn, tenant)
    assert rec["computed_status"] in ("recomendado", "inconclusivo")
    as_user(db_conn, tenant.user_id, "select submit_recommendation(%s)", (rec["id"],))
    as_user(db_conn, ADMIN, "select approve_recommendation(%s)", (rec["id"],))
    as_user(db_conn, tenant.user_id, "select request_report(%s)", (rec["id"],))
    pipe.drain()
    rec = recommendation(db_conn, tenant)
    assert rec["status"] == "emitida"
    pdf = tenant.storage.objects[rec["pdf_path"]]
    assert pdf[:4] == b"%PDF" and hashlib.sha256(pdf).hexdigest() == rec["pdf_sha256"].strip()


@pytest.mark.samples
def test_livro_with_other_cnpj_is_blocked(db_conn, sample):
    t = TenantFixture(db_conn, cnpj="11222333000181")
    try:
        file_id = t.add_file(sample("livro_202608"), "livro.pdf")
        Pipeline(db_conn, t.storage).drain()
        row = db_conn.execute("select status, error_code, doc_type from source_files where id = %s", (file_id,)).fetchone()
        assert (row["status"], row["error_code"]) == ("cnpj_mismatch", "CNPJ_MISMATCH")
    finally:
        t.cleanup()
