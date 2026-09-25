"""AT-007: validações internas fecham nas amostras e acusam valor adulterado."""
from decimal import Decimal

import pytest

from worker.pipeline import parse_document
from worker.validations import validate

from conftest import ALL_SAMPLE_FILES

NAMES = sorted(ALL_SAMPLE_FILES)   # 12 documentos: 06, 07 e 08/2026


@pytest.mark.samples
@pytest.mark.parametrize("name", NAMES)
def test_samples_pass_all_internal_validations(sample, name):
    _, validations = parse_document(sample(name))
    assert len(validations) >= 4
    failing = [v.rule for v in validations if v.status != "pass"]
    assert failing == []


def _tamper(result, key, column=None, section=None, delta=Decimal("10.00")):
    for v in result.values:
        if v.field_key == key and (column is None or v.column == column) and (section is None or v.section == section):
            v.value += delta
            return
    raise AssertionError("valor não encontrado: " + key)


@pytest.mark.samples
@pytest.mark.parametrize("name, key, column, section, rule", [
    ("pgdas_202608", "tributo.irpj", "irpj", "2.7.estab1.atividade1", "pgdas.tributos_igual_total[2.7.estab1.atividade1]"),
    ("folha_202608", "rubrica.001", "total", None, "folha.soma_rubricas_igual_total_adicionais"),
    ("dre_202608", "conta.3.1.1.01.001", None, None, "dre.soma_contas_devedoras_igual_despesas"),
    ("balancete_202608", "conta.20308", "credito", None, "balancete.saldo_anterior_mais_movimento_igual_saldo_atual"),
])
def test_tampered_value_fails_validation(sample, name, key, column, section, rule):
    result, _ = parse_document(sample(name))
    _tamper(result, key, column, section)
    by_rule = {v.rule: v for v in validate(result)}
    assert by_rule[rule].status == "fail"


def test_non_monthly_period_is_flagged():
    from worker.models import DocType, ParseResult

    result = ParseResult(doc_type=DocType.DRE_ALTERDATA, parser_version="t", cnpj="1" * 14,
                         competence="2026-08", pages=1, values=[])
    by_rule = {v.rule: v for v in validate(result, monthly=False)}
    assert by_rule["periodo_mensal"].status == "fail"


@pytest.mark.samples
def test_credit_account_inside_expenses_reduces_expenses(sample):
    """DRE 06/2026: "Vale Transporte" credora (366,93) no grupo de despesas reduz a despesa, não é receita."""
    from worker.validations import dre_groups, signed_total

    result, validations = parse_document(sample("dre_202606"))
    receitas, despesas = dre_groups(result.values)
    vt = [v for v in despesas if v.label == "Vale Transporte"]
    assert vt and vt[0].nature == "C" and vt[0].value == Decimal("366.93")
    assert not [v for v in receitas if v.label == "Vale Transporte"]
    assert signed_total(despesas, "D") == Decimal("108663.59")
    assert [v.rule for v in validations if v.status != "pass"] == []
