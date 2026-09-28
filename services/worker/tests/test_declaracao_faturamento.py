"""Ciclo 5 — AT-501 a AT-503: Declaração de Faturamento (planejamento rápido)."""
from decimal import Decimal

import pytest

from conftest import SAMPLE_CNPJ, TenantFixture
from worker.classify import classify
from worker.models import DocType
from worker.pdf.layout import read_rows
from worker.pipeline import Pipeline, parse_document
from worker.validations import validate


@pytest.mark.samples
def test_declaracao_is_parsed_with_12_months_and_total(sample):
    rows, _ = read_rows(sample("declaracao_202608"))
    cls = classify(rows)
    assert (cls.doc_type, cls.cnpj) == (DocType.DECLARACAO_FATURAMENTO, SAMPLE_CNPJ)
    assert (str(cls.period_start), str(cls.period_end)) == ("2025-09-01", "2026-08-31")
    result, checks = parse_document(sample("declaracao_202608"))
    meses = [v for v in result.values if v.field_key == "faturamento.mes"]
    assert [v.competence for v in meses] == [f"2025-{m:02d}" for m in range(9, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]
    assert meses[0].value == Decimal("315728.44") and meses[-1].value == Decimal("203180.77")
    assert next(v.value for v in result.values if v.field_key == "total_geral") == Decimal("3719883.51")
    assert all(v.page == 1 and v.bbox for v in result.values)
    assert {c.rule: c.status for c in checks} == {"faturamento.soma_igual_total": "pass",
                                                   "faturamento.12_meses_consecutivos": "pass"}


@pytest.mark.samples
def test_tampered_month_fails_total_check(sample):
    result, _ = parse_document(sample("declaracao_202608"))
    for v in result.values:
        if v.field_key == "faturamento.mes" and v.competence == "2026-01":
            v.value += Decimal("0.02")
    failed = {c.rule for c in validate(result) if c.status == "fail"}
    assert failed == {"faturamento.soma_igual_total"}


@pytest.mark.samples
def test_missing_month_fails_sequence_check(sample):
    result, _ = parse_document(sample("declaracao_202608"))
    result.values[:] = [v for v in result.values if v.competence != "2026-03" or v.field_key != "faturamento.mes"]
    checks = {c.rule: c.status for c in validate(result)}
    assert checks["faturamento.12_meses_consecutivos"] == "fail"


@pytest.mark.db
@pytest.mark.samples
def test_declaracao_with_other_cnpj_is_blocked(db_conn, sample):
    t = TenantFixture(db_conn, cnpj="11222333000181")
    try:
        file_id = t.add_file(sample("declaracao_202608"), "declaracao.pdf")
        Pipeline(db_conn, t.storage).drain()
        row = db_conn.execute("select status, error_code from source_files where id = %s", (file_id,)).fetchone()
        assert (row["status"], row["error_code"]) == ("cnpj_mismatch", "CNPJ_MISMATCH")
    finally:
        t.cleanup()
