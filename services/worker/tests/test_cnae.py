"""Ciclo 5 — AT-510, AT-511: tabela CNAE → anexo (prefixo mais longo, vedações, fora da tabela)."""
import pytest

from worker.engine.cnae import format_cnae
from worker.engine.rules import RulesError


def test_sample_cnae_suggests_anexo_i(cnae_table):
    m = cnae_table.match("4744001")
    assert (m.prefixo, m.profile.anexo, m.profile.presumido, m.profile.fator_r, m.vedado) == (
        "47", "I", "comercio_industria", False, False)
    assert format_cnae("4744001") == "4744-0/01"
    assert cnae_table.match("4744-0/01").profile.anexo == "I"      # aceita o CNAE formatado


@pytest.mark.parametrize("cnae, prefixo, anexo, extra", [
    ("4731800", "4731", "I", "revenda_combustiveis"),          # exceção por classe dentro do comércio
    ("4520001", "4520", "III", "servicos_gerais"),             # serviço de reparação dentro da divisão 45
    ("6201501", "62", "V", "fator_r"),
    ("6911701", "6911", "IV", "servicos_gerais"),
])
def test_longest_prefix_wins(cnae_table, cnae, prefixo, anexo, extra):
    m = cnae_table.match(cnae)
    assert (m.prefixo, m.profile.anexo) == (prefixo, anexo)
    assert m.profile.fator_r if extra == "fator_r" else m.profile.presumido == extra


def test_prohibited_activity_is_flagged(cnae_table):
    assert cnae_table.match("4636202").vedado
    assert cnae_table.match("1220401").vedado


def test_unknown_cnae_has_no_suggestion(cnae_table):
    assert cnae_table.match("0111301") is None           # agricultura: fora da tabela
    assert cnae_table.match("123") is None
    assert cnae_table.match(None) is None


def test_table_is_versioned_and_unverified(cnae_table):
    assert cnae_table.version and len(cnae_table.hash) == 64 and not cnae_table.verified


def test_duplicate_prefix_is_rejected(tmp_path):
    from worker.engine.cnae import load_cnae_table

    p = tmp_path / "t.json"
    entry = '{"prefixo": "47", "anexo": "I", "presumido": "comercio_industria", "fator_r": false, "vedado": false, "nota": ""}'
    p.write_text('{"versao": "x", "entradas": [' + entry + ", " + entry + "]}", encoding="utf-8")
    with pytest.raises(RulesError):
        load_cnae_table(p)
