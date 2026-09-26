"""Ciclo 4 — Livro de Apuração do ICMS (Alterdata): extração por CFOP, totais conferidos e conciliação R7."""
from decimal import Decimal

import pytest

from conftest import DEFAULT_MAPPINGS, SAMPLE_CNPJ
from test_reconcile import facts_from
from worker.models import DocType
from worker.pipeline import parse_document
from worker.reconcile import Facts, reconcile
from worker.validations import validate


def _value(result, section, key, column="valor_contabil"):
    return next(v.value for v in result.values if v.section == section and v.field_key == key and v.column == column)


@pytest.mark.samples
def test_livro_is_parsed_with_totals(sample):
    result, checks = parse_document(sample("livro_202608"))
    assert result.doc_type == DocType.LIVRO_ICMS_ALTERDATA
    assert (result.cnpj, result.competence) == (SAMPLE_CNPJ, "2026-08")
    assert _value(result, "entradas", "total") == Decimal("158503.98")
    assert _value(result, "saidas", "total") == Decimal("205577.54")
    assert _value(result, "entradas", "cfop.2102") == Decimal("74228.48")
    # subtotal em duas linhas ("2.00 De Outros" + "Estados <valores>")
    assert _value(result, "entradas", "subtotal.2.00") == Decimal("141814.07")
    assert all(v.page == 1 and v.bbox for v in result.values)
    assert checks and all(c.status == "pass" for c in checks)


@pytest.mark.samples
def test_tampered_cfop_fails_validation(sample):
    result, _ = parse_document(sample("livro_202608"))
    for v in result.values:
        if v.section == "entradas" and v.field_key == "cfop.1102" and v.column == "valor_contabil":
            v.value += Decimal("10.00")
    failed = {c.rule for c in validate(result) if c.status == "fail"}
    assert failed == {"livro.soma_cfop_igual_total[entradas.valor_contabil]"}


NAMES_R7 = ["pgdas_202608", "balancete_202608", "livro_202608"]


@pytest.mark.samples
def test_r7_purchases_match_balancete(sample):
    results = reconcile(Facts(facts_from(sample, NAMES_R7)), DEFAULT_MAPPINGS, Decimal("1.00"))
    r7 = next(r for r in results if r.rule == "R7")
    assert (r7.competence, r7.status) == ("2026-08", "ok")
    assert r7.left_value == Decimal("149985.71") == r7.right_value     # 1102 + 2102 + 1403 + 2403


@pytest.mark.samples
def test_r7_divergence_and_absence(sample):
    facts = facts_from(sample, NAMES_R7, adjust=((DocType.LIVRO_ICMS_ALTERDATA, "cfop.2403", "valor_contabil"),
                                                  Decimal("5.00")))
    r7 = next(r for r in reconcile(Facts(facts), DEFAULT_MAPPINGS, Decimal("1.00")) if r.rule == "R7")
    assert (r7.status, r7.diff) == ("divergent", Decimal("5.00"))
    # sem livro, R7 não existe (documento opcional)
    without = reconcile(Facts(facts_from(sample, NAMES_R7[:2])), DEFAULT_MAPPINGS, Decimal("1.00"))
    assert "R7" not in {r.rule for r in without}
