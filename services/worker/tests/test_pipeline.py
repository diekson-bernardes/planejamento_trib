"""Integração com o Postgres local: AT-011, AT-012, AT-015 e isolamento por office_id."""
import psycopg
import pytest

from conftest import TenantFixture, minimal_pdf
from worker.pipeline import Pipeline

pytestmark = [pytest.mark.db]


def file_row(conn, file_id):
    return conn.execute("select * from source_files where id = %s", (file_id,)).fetchone()


def value_count(conn, file_id):
    return conn.execute("select count(*) as n from extracted_values where file_id = %s", (file_id,)).fetchone()["n"]


@pytest.mark.samples
def test_extraction_is_idempotent(db_conn, tenant, sample):
    data = sample("pgdas_202608")
    file_id = tenant.add_file(data, "pgdas.pdf")
    pipe = Pipeline(db_conn, tenant.storage)
    pipe.drain()

    first = file_row(db_conn, file_id)
    assert first["status"] == "extracted"
    assert first["doc_type"] == "PGDAS_D"
    n1 = value_count(db_conn, file_id)
    assert n1 > 0

    # retry/reprocessamento do mesmo arquivo: nova chave, mesmo resultado
    with db_conn.transaction():
        db_conn.execute(
            "insert into jobs (office_id, kind, payload, idempotency_key) values "
            "(%s, 'extract', jsonb_build_object('file_id', %s::text, 'case_id', %s::text), %s)",
            (tenant.office_id, file_id, tenant.case_id, f"extract:{file_id}:retry"),
        )
    pipe.drain()
    second = file_row(db_conn, file_id)
    assert second["status"] == "extracted"
    assert second["result_hash"] == first["result_hash"]
    assert value_count(db_conn, file_id) == n1

    # todas as linhas gravadas pelo worker (service role) carregam o escritório do dossiê
    for table in ("extracted_values", "validations", "reconciliations", "jobs"):
        other = db_conn.execute(
            f"select count(*) as n from {table} where office_id <> %s and "
            + ("case_id = %s" if table != "jobs" else "payload ->> 'case_id' = %s::text"),
            (tenant.office_id, tenant.case_id),
        ).fetchone()["n"]
        assert other == 0, table


@pytest.mark.samples
def test_duplicate_hash_in_same_case_is_rejected(db_conn, tenant, sample):
    data = sample("dre_202608")
    tenant.add_file(data, "dre.pdf")
    with pytest.raises(psycopg.errors.UniqueViolation):
        tenant.add_file(data, "dre-copia.pdf")


@pytest.mark.samples
def test_cnpj_mismatch_blocks_file(db_conn, sample):
    t = TenantFixture(db_conn, cnpj="11222333000181")
    try:
        file_id = t.add_file(sample("folha_202608"), "folha.pdf")
        Pipeline(db_conn, t.storage).drain()
        row = file_row(db_conn, file_id)
        assert row["status"] == "cnpj_mismatch"
        assert row["error_code"] == "CNPJ_MISMATCH"
        assert value_count(db_conn, file_id) == 0
    finally:
        t.cleanup()


def test_pdf_without_text_is_rejected_without_values(db_conn, tenant):
    file_id = tenant.add_file(minimal_pdf(None), "escaneado.pdf")
    Pipeline(db_conn, tenant.storage).drain()
    row = file_row(db_conn, file_id)
    assert row["status"] == "rejected"
    assert row["error_code"] == "NO_TEXT"
    assert value_count(db_conn, file_id) == 0


def test_unknown_document_is_unclassified(db_conn, tenant):
    file_id = tenant.add_file(minimal_pdf("Documento qualquer"), "outro.pdf")
    Pipeline(db_conn, tenant.storage).drain()
    assert file_row(db_conn, file_id)["status"] == "unclassified"


@pytest.mark.samples
def test_layout_change_fails_with_parser_version(db_conn, tenant, sample):
    # DRE forçada como balancete: âncora do balancete ausente → falha sem valores parciais
    file_id = tenant.add_file(sample("dre_202608"), "dre.pdf")
    with db_conn.transaction():
        db_conn.execute("update jobs set payload = payload || '{\"manual_doc_type\": \"BALANCETE_ALTERDATA\"}' "
                        "where payload ->> 'file_id' = %s::text", (file_id,))
    Pipeline(db_conn, tenant.storage).drain()
    row = file_row(db_conn, file_id)
    assert row["status"] == "failed"
    assert row["error_code"] == "LAYOUT"
    assert row["parser_version"] == "balancete-alterdata-1.0.0"
    assert value_count(db_conn, file_id) == 0


@pytest.mark.samples
def test_file_with_adjustments_is_not_reprocessed(db_conn, tenant, sample):
    file_id = tenant.add_file(sample("dre_202608"), "dre.pdf")
    pipe = Pipeline(db_conn, tenant.storage)
    pipe.drain()
    with db_conn.transaction():
        vid = db_conn.execute("select id from extracted_values where file_id = %s order by ordinal limit 1",
                              (file_id,)).fetchone()["id"]
        db_conn.execute("insert into value_adjustments (value_id, new_value, reason, author) values (%s, 1, %s, %s)",
                        (vid, "ajuste de teste", tenant.user_id))
        db_conn.execute("insert into jobs (office_id, kind, payload, idempotency_key) values "
                        "(%s, 'extract', jsonb_build_object('file_id', %s::text, 'case_id', %s::text), %s)",
                        (tenant.office_id, file_id, tenant.case_id, f"extract:{file_id}:again"))
    pipe.drain()
    row = file_row(db_conn, file_id)
    assert row["status"] == "extracted"  # reprocessamento ignorado sem quebrar o dossiê
    job = db_conn.execute("select status, last_error from jobs where idempotency_key = %s",
                          (f"extract:{file_id}:again",)).fetchone()
    assert (job["status"], job["last_error"]) == ("done", "HAS_ADJUSTMENTS")
    assert value_count(db_conn, file_id) > 0  # valores e ajuste preservados


def test_corrupt_pdf_is_rejected_without_retry(db_conn, tenant):
    file_id = tenant.add_file(b"%PDF-1.4\n\x00\x01 lixo sem estrutura", "corrompido.pdf")
    Pipeline(db_conn, tenant.storage).drain()
    row = file_row(db_conn, file_id)
    assert (row["status"], row["error_code"]) == ("rejected", "NOT_PDF")
    attempts = db_conn.execute("select attempts from jobs where payload ->> 'file_id' = %s::text",
                               (file_id,)).fetchone()["attempts"]
    assert attempts == 1
