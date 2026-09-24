"""Parser da Demonstração do Resultado do Exercício (Alterdata)."""
import re

from worker.classify import classify
from worker.errors import LayoutNotRecognized
from worker.models import DocType, ParseResult, Row
from worker.parsers.base import ValueCollector, money_words, require_anchor

PARSER_VERSION = "dre-alterdata-1.0.0"

CLASSIFICACAO = re.compile(r"\d+(\.\d+)+")
TOTAL_PREFIX = re.compile(r"^=\s*T\s*o\s*t\s*a\s*l\s*-\s*")
SIGNATURE = "Declaro, sob as penas da lei"
RESULTADO = [
    ("RECEITAS", "resultado.receitas", "Receitas"),
    ("DESPESAS + CUSTO", "resultado.despesas_custos", "Despesas + custo"),
    ("LUCRO LÍQUIDO DO EXERCÍCIO", "resultado.lucro_liquido", "Lucro líquido do exercício"),
    ("PREJUÍZO", "resultado.lucro_liquido", "Prejuízo do exercício"),
]


def subtotal_name(text: str) -> str:
    """'=T o t a l - RECEITAS' → 'RECEITAS'; '=CUSTO C/ PESSOAL' → 'CUSTO C/ PESSOAL'."""
    name = TOTAL_PREFIX.sub("", text)
    return name.lstrip("=").strip()


class DreAlterdataParser:
    DOC_TYPE = DocType.DRE_ALTERDATA
    PARSER_VERSION = PARSER_VERSION

    def parse(self, rows: list[Row], pages: int) -> ParseResult:
        cls = classify(rows, DocType.DRE_ALTERDATA)
        if not cls.cnpj or not cls.competence:
            raise LayoutNotRecognized("CNPJ ou período ausente (parser " + PARSER_VERSION + ")")
        require_anchor(rows, "Descrição Classificação", PARSER_VERSION)
        require_anchor(rows, "RESULTADO DO EXERCÍCIO", PARSER_VERSION)
        c = ValueCollector(cls.competence)

        in_body = False
        in_result = False
        for row in rows:
            text = row.text
            if text.startswith("Descrição Classificação"):
                in_body = True
                continue
            if SIGNATURE in text:
                in_body = False
                continue
            if not in_body:
                continue
            if text.startswith("RESULTADO DO EXERCÍCIO"):
                in_result = True
                continue
            mw = money_words(row)
            if in_result:
                if mw:
                    self._resultado(row, mw, c)
                continue
            if not mw:
                continue  # cabeçalho de grupo (sem valor)
            w, value, nature = mw[-1]
            label_tokens = [x.text for x in row.words if x is not w]
            if text.startswith("="):
                raw = " ".join(label_tokens)
                name = subtotal_name(raw)
                prefix = "total." if TOTAL_PREFIX.match(raw) else "subtotal."
                c.add(section="subtotal", field_key=prefix + name, label=name, value=value,
                      nature=nature, page=row.page, bbox=w.bbox)
                continue
            code = next((t for t in label_tokens if CLASSIFICACAO.fullmatch(t)), None)
            if code is None:
                raise LayoutNotRecognized("conta da DRE sem classificação (parser " + PARSER_VERSION + ")")
            label = " ".join(t for t in label_tokens if t != code)
            c.add(section="conta", field_key="conta." + code, label=label, value=value, nature=nature,
                  page=row.page, bbox=w.bbox, account_code=code)

        if c.find("resultado.lucro_liquido") is None:
            raise LayoutNotRecognized("resultado do exercício ausente (parser " + PARSER_VERSION + ")")
        return ParseResult(
            doc_type=DocType.DRE_ALTERDATA, parser_version=PARSER_VERSION, cnpj=cls.cnpj,
            competence=cls.competence, pages=pages, values=c.values,
        )

    @staticmethod
    def _resultado(row: Row, mw, c: ValueCollector) -> None:
        text = " ".join(x.text for x in row.words if x is not mw[-1][0]).replace("-", " ")
        text = re.sub(r"\s+", " ", text).strip().rstrip(":").strip()
        for prefix, key, label in RESULTADO:
            if text.startswith(prefix):
                w, value, nature = mw[-1]
                c.add(section="resultado", field_key=key, label=label, value=value, nature=nature,
                      page=row.page, bbox=w.bbox)
                return
