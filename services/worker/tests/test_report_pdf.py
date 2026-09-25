"""AT-218: PDF executivo com as seções exigidas e SHA-256 reprodutível (ReportLab invariant)."""
from decimal import Decimal
from io import BytesIO

import pdfplumber
import pytest

from conftest import golden_assumptions_06_08
from worker.engine.decision import project
from worker.engine.snapshot import SnapshotView
from worker.report_pdf import ReportData, build_recommendation_pdf, sha256

pytestmark = pytest.mark.samples


@pytest.fixture(scope="module")
def report(snapshot_content_06_08, rules, golden, decision_params):
    view = SnapshotView(snapshot_content_06_08)
    a = golden_assumptions_06_08(view, rules, golden)
    res = project(view, a, rules, decision_params, Decimal("0.05"))
    return ReportData(
        recommendation_id="rec-teste", office_name="Escritório Teste", legal_name="Empresa Teste Ltda",
        cnpj="37704456000142", year=res.projected.year, rules_version=rules.version, rules_hash=rules.hash,
        decision_version=decision_params.version, decision_hash=decision_params.hash, snapshot_sha256="a" * 64,
        result_hash=res.result_hash, threshold=Decimal("0.05"), result=res.summary(),
        sensitivity=[s.as_dict() for s in res.sensitivity], computed=res.recommendation.as_dict(),
        assumptions=[{"key": r["key"], "scope": r["scope"], "label": r["key"], "value": r["value"],
                      "justification": "Orçamento do cliente" if r["key"] == "projecao.receita" else None}
                     for r in a.rows],
        lines=res.lines(), events=[{"event": "created", "comment": None}, {"event": "submitted", "comment": None},
                                   {"event": "approved", "comment": None}],
        approver_name="Maria Contadora", approver_crc="SP-123456/O-7", approved_at="25/09/2026 15:00",
    )


def test_pdf_has_required_sections(report):
    data = build_recommendation_pdf(report)
    with pdfplumber.open(BytesIO(data)) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    for expected in ("Planejamento tributário — exercício 2026", "37.704.456/0001-42", "Data-base normativa",
                     "Recomendação", "Comparativo do exercício", "O regime tributário com maior vantagem",
                     "Sensibilidade e ponto de virada", "Resultado mensal por regime", "Premissas", "Ressalvas",
                     "Reforma Tributária", "Maria Contadora", "SP-123456/O-7", "25/09/2026 15:00", "Orçamento do cliente"):
        assert expected in text, expected


def test_same_input_same_bytes(report):
    assert sha256(build_recommendation_pdf(report)) == sha256(build_recommendation_pdf(report))
