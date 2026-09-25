"""AT-022 (smoke): dossiê padrão de 6 PDFs fica "pronto para revisão" em até 5 minutos,
com a conciliação de ago/2026 idêntica ao golden."""
import time
from decimal import Decimal

import pytest

from conftest import SAMPLE_FILES
from worker.pipeline import Pipeline

pytestmark = [pytest.mark.db, pytest.mark.samples]

LIMIT_SECONDS = 300


def test_six_pdfs_ready_for_review_within_limit(db_conn, tenant, sample, golden):
    for name in SAMPLE_FILES:
        tenant.add_file(sample(name), name + ".pdf")
    started = time.monotonic()
    Pipeline(db_conn, tenant.storage).drain()
    elapsed = time.monotonic() - started

    case = db_conn.execute("select status from tax_cases where id = %s", (tenant.case_id,)).fetchone()
    assert case["status"] == "review"
    statuses = db_conn.execute("select status from source_files where case_id = %s", (tenant.case_id,)).fetchall()
    assert [s["status"] for s in statuses] == ["extracted"] * 6
    assert elapsed <= LIMIT_SECONDS, f"levou {elapsed:.1f}s"

    rows = db_conn.execute(
        "select to_char(competence, 'YYYY-MM') as competence, rule, left_value, right_value, diff, status "
        "from reconciliations where case_id = %s order by competence, rule", (tenant.case_id,)
    ).fetchall()
    expected = golden("reconciliation_202608")["results"]

    def fmt(v):
        return None if v is None else str(Decimal(v).quantize(Decimal("0.01")))

    assert [{"competence": r["competence"], "rule": r["rule"], "left_value": fmt(r["left_value"]),
             "right_value": fmt(r["right_value"]), "diff": fmt(r["diff"]), "status": r["status"]}
            for r in rows] == expected
    print(f"\n[AT-022] 6 PDFs prontos para revisão em {elapsed:.2f}s (limite {LIMIT_SECONDS}s)")
