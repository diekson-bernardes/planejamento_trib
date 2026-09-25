"""AT-002 a AT-006, AT-014: extração de todas as linhas = golden, origem de cada valor e layout alterado."""
import pytest

from worker.classify import classify
from worker.errors import LayoutNotRecognized
from worker.models import Row
from worker.parsers import get_parser
from worker.pdf.layout import read_rows

GOLDEN_NAMES = ["pgdas_202606", "pgdas_202607", "pgdas_202608", "folha_202608", "dre_202608", "balancete_202608"]


def normalize(v) -> dict:
    return {"ordinal": v.ordinal, "section": v.section, "field_key": v.field_key, "column": v.column,
            "account_code": v.account_code, "competence": v.competence, "value": str(v.value),
            "nature": v.nature, "page": v.page}


def parse(data: bytes):
    rows, pages = read_rows(data)
    return get_parser(classify(rows).doc_type).parse(rows, pages)


@pytest.mark.samples
@pytest.mark.parametrize("name", GOLDEN_NAMES)
def test_all_lines_match_golden(sample, golden, name):
    expected = golden(name)
    result = parse(sample(name))
    assert result.doc_type.value == expected["doc_type"]
    assert result.parser_version == expected["parser_version"]
    assert result.cnpj == expected["cnpj"]
    assert result.competence == expected["competence"]
    assert [normalize(v) for v in result.values] == expected["values"]


@pytest.mark.samples
@pytest.mark.parametrize("name", GOLDEN_NAMES)
def test_every_value_has_origin(sample, name):
    result = parse(sample(name))
    assert result.values
    for v in result.values:
        assert 1 <= v.page <= result.pages
        x0, top, x1, bottom = v.bbox
        assert x1 >= x0 and bottom >= top


@pytest.mark.samples
def test_key_values_of_august(sample):
    pgdas = parse(sample("pgdas_202608"))
    folha = parse(sample("folha_202608"))
    dre = parse(sample("dre_202608"))

    def get(res, key, column=None, section=None):
        return next(str(v.value) for v in res.values if v.field_key == key
                    and (column is None or v.column == column) and (section is None or v.section == section))

    assert get(pgdas, "receita.rpa", "total") == "203180.77"
    assert get(pgdas, "tributo.total", "total", "2.8.total_declarado") == "23430.47"
    assert get(folha, "total_adicionais", "total") == "34212.13"
    assert get(folha, "total_descontos", "total") == "4361.13"
    assert get(folha, "total_liquido", "total") == "29851.00"
    assert get(folha, "total_funcionarios", "total") == "12"
    assert get(dre, "resultado.lucro_liquido") == "126353.14"
    rubrica_141 = [v for v in folha.values if v.field_key == "rubrica.141" and v.column == "total"]
    assert len(rubrica_141) == 2  # código repetido na folha: chave natural não é única


@pytest.mark.samples
@pytest.mark.parametrize("name, anchor", [
    ("pgdas_202608", "2.8) Total Geral da Empresa"),
    ("folha_202608", "TOTAL DE ADICIONAIS"),
    ("dre_202608", "RESULTADO DO EXERCÍCIO"),
    ("balancete_202608", "Descrição Saldo Anterior"),
])
def test_missing_anchor_fails_without_partial_values(sample, name, anchor):
    rows, pages = read_rows(sample(name))
    doc_type = classify(rows).doc_type
    broken: list[Row] = [r for r in rows if anchor not in r.text]
    with pytest.raises(LayoutNotRecognized) as exc:
        get_parser(doc_type).parse(broken, pages)
    assert "parser " in str(exc.value)
