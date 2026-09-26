"""Integração com o Postgres local — AT-205, AT-211, AT-218, AT-219, AT-221.

Fluxo real: 12 PDFs → homologação → premissas → projeção → envio → aprovação (responsável técnico) → PDF emitido."""
import hashlib
import json
import time

import psycopg
import pytest

from conftest import ALL_SAMPLE_FILES
from worker.pipeline import Pipeline

pytestmark = [pytest.mark.db, pytest.mark.samples]
ADMIN = "a1111111-1111-4111-8111-111111111111"      # admin do seed: vira responsável técnico no escritório do teste
LIMIT_SECONDS = 60


def as_user(conn, user_id: str, sql: str, params: tuple = ()):
    with conn.transaction():
        conn.execute("select set_config('request.jwt.claims', %s, true)",
                     (json.dumps({"sub": user_id, "role": "authenticated"}),))
        return conn.execute(sql, params).fetchall()


def prepare(db_conn, tenant, sample):
    with db_conn.transaction():
        db_conn.execute("insert into office_members (office_id, user_id, role) values (%s, %s, 'analyst'), (%s, %s, 'admin')",
                        (tenant.office_id, tenant.user_id, tenant.office_id, ADMIN))
    for name in ALL_SAMPLE_FILES:
        tenant.add_file(sample(name), name + ".pdf")
    pipe = Pipeline(db_conn, tenant.storage)
    pipe.drain()
    # 06 e 07/2026 têm divergência real em R5 (salários a pagar): o analista justifica, como na tela
    as_user(db_conn, tenant.user_id, "update reconciliations set justification = 'Divergência conferida no teste' "
            "where case_id = %s and status = 'divergent' returning id", (tenant.case_id,))
    as_user(db_conn, tenant.user_id, "select * from homologate_case(%s)", (tenant.case_id,))
    as_user(db_conn, tenant.user_id, "select request_planning(%s)", (tenant.case_id,))
    pipe.drain()
    return pipe


def confirm_all(db_conn, tenant, golden, only_keys=None):
    decl = golden("motor_202606_08")["assumption_overrides"]
    # o grupo reforma_2027 fica pendente: não bloqueia a projeção de 2026 (ciclo 4)
    rows = db_conn.execute("select id, key, suggested_value from assumptions where case_id = %s and status = 'pending' "
                           "and grp <> 'reforma_2027'", (tenant.case_id,)).fetchall()
    for r in rows:
        if only_keys is not None and r["key"] not in only_keys:
            continue
        value, reason = (decl[r["key"]], "Declaração do cliente em teste") if r["key"] in decl else (r["suggested_value"], None)
        as_user(db_conn, tenant.user_id, "select confirm_assumption(%s, %s::jsonb, %s)", (r["id"], json.dumps(value), reason))


def recommendation(db_conn, tenant):
    return db_conn.execute(
        "select r.*, p.recommendation as computed, p.duration_ms from recommendations r "
        "join projections p on p.id = r.projection_id where r.case_id = %s order by r.created_at desc limit 1",
        (tenant.case_id,)).fetchone()


def events(db_conn, rec_id):
    return [e["event"] for e in db_conn.execute(
        "select event from recommendation_events where recommendation_id = %s order by id", (rec_id,)).fetchall()]


def test_projection_blocked_while_premises_are_pending(db_conn, tenant, sample, golden):
    pipe = prepare(db_conn, tenant, sample)
    as_user(db_conn, tenant.user_id, "select request_projection(%s)", (tenant.case_id,))
    pipe.drain()
    rec = recommendation(db_conn, tenant)
    assert rec["computed_status"] == "bloqueado" and "pendente" in rec["computed"]["bloqueios"][0]   # AT-211
    with pytest.raises(psycopg.errors.RaiseException, match="bloqueada"):
        as_user(db_conn, tenant.user_id, "select submit_recommendation(%s)", (rec["id"],))


def test_full_decision_flow(db_conn, tenant, sample, golden):
    pipe = prepare(db_conn, tenant, sample)
    confirm_all(db_conn, tenant, golden)
    as_user(db_conn, ADMIN, "select set_technical_responsible(%s, %s, true, 'Maria Contadora', 'SP-123456/O-7')",
            (tenant.office_id, ADMIN))

    started = time.monotonic()
    as_user(db_conn, tenant.user_id, "select request_projection(%s)", (tenant.case_id,))
    pipe.drain()
    elapsed = time.monotonic() - started
    assert elapsed <= LIMIT_SECONDS, f"{elapsed:.1f}s"                                  # AT-221
    rec = recommendation(db_conn, tenant)
    assert rec["status"] == "rascunho" and rec["computed_status"] in ("recomendado", "inconclusivo")
    assert str(rec["elaborated_by"]) == tenant.user_id
    print(f"\n[AT-221] projeção + sensibilidade + recomendação em {elapsed:.2f}s ({rec['duration_ms']} ms no worker)")

    # AT-205: mesmo pedido → nenhuma projeção nova
    as_user(db_conn, tenant.user_id, "select request_projection(%s)", (tenant.case_id,))
    pipe.drain()
    assert db_conn.execute("select count(*) as n from projections where case_id = %s",
                           (tenant.case_id,)).fetchone()["n"] == 1

    as_user(db_conn, tenant.user_id, "select submit_recommendation(%s)", (rec["id"],))
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="responsável técnico"):          # AT-215
        as_user(db_conn, tenant.user_id, "select approve_recommendation(%s)", (rec["id"],))
    as_user(db_conn, ADMIN, "select approve_recommendation(%s)", (rec["id"],))
    as_user(db_conn, tenant.user_id, "select request_report(%s)", (rec["id"],))
    pipe.drain()

    rec = recommendation(db_conn, tenant)
    assert rec["status"] == "emitida" and str(rec["approved_by"]) == ADMIN
    pdf = tenant.storage.objects[rec["pdf_path"]]
    assert pdf[:4] == b"%PDF" and hashlib.sha256(pdf).hexdigest() == rec["pdf_sha256"].strip()        # AT-218
    assert events(db_conn, rec["id"]) == ["created", "submitted", "approved", "emission_requested", "emitted"]

    # AT-219: premissa alterada depois da emissão → PDF emitido intacto; a recomendação emitida não muda
    rat = db_conn.execute("select id from assumptions where case_id = %s and key = 'folha.rat'",
                          (tenant.case_id,)).fetchone()
    as_user(db_conn, tenant.user_id, "select confirm_assumption(%s, '\"0.03\"'::jsonb, 'CNAE de risco grave')", (rat["id"],))
    after = db_conn.execute("select status, pdf_sha256 from recommendations where id = %s", (rec["id"],)).fetchone()
    assert after["status"] == "emitida" and after["pdf_sha256"] == rec["pdf_sha256"]
    assert tenant.storage.objects[rec["pdf_path"]] == pdf

    # nova projeção com a premissa alterada → nova recomendação; aprovada e premissa alterada → volta a rascunho
    as_user(db_conn, tenant.user_id, "select request_projection(%s)", (tenant.case_id,))
    pipe.drain()
    new = recommendation(db_conn, tenant)
    assert new["id"] != rec["id"]
    as_user(db_conn, tenant.user_id, "select submit_recommendation(%s)", (new["id"],))
    as_user(db_conn, ADMIN, "select approve_recommendation(%s)", (new["id"],))
    as_user(db_conn, tenant.user_id, "select confirm_assumption(%s, '\"0.02\"'::jsonb, 'Voltou ao CNAE original')", (rat["id"],))
    new = recommendation(db_conn, tenant)
    assert new["status"] == "rascunho" and new["approved_by"] is None
    assert events(db_conn, new["id"])[-1] == "reset_by_assumption"
