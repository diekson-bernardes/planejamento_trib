"""Parser da Declaração de Faturamento (planejamento rápido): faturamento mês a mês dos últimos 12 meses e Total Geral."""
import re

from worker.classify import classify
from worker.errors import LayoutNotRecognized
from worker.models import DocType, ParseResult, Row
from worker.parsers.base import ValueCollector, money_words, require_anchor

PARSER_VERSION = "declaracao-faturamento-1.0.0"
MONTH_ROW = re.compile(r"^(\d\d)/(\d\d\d\d)\s")


class DeclaracaoFaturamentoParser:
    DOC_TYPE = DocType.DECLARACAO_FATURAMENTO
    PARSER_VERSION = PARSER_VERSION

    def parse(self, rows: list[Row], pages: int) -> ParseResult:
        cls = classify(rows, DocType.DECLARACAO_FATURAMENTO)
        if not cls.cnpj or not cls.competence:
            raise LayoutNotRecognized("CNPJ ou período ausente (parser " + PARSER_VERSION + ")")
        start = require_anchor(rows, "Faturamento (R$)", PARSER_VERSION)
        c = ValueCollector(cls.competence)
        for row in rows[start + 1:]:
            text = row.text.strip()
            mw = money_words(row)
            m = MONTH_ROW.match(text)
            if m and len(mw) == 1:
                word, value, _ = mw[0]
                c.add(section="faturamento", field_key="faturamento.mes", label=m.group(1) + "/" + m.group(2),
                      value=value, page=row.page, bbox=(word.x0, word.top, word.x1, word.bottom),
                      competence=f"{m.group(2)}-{m.group(1)}")
            elif text.startswith("Total Geral") and len(mw) == 1:
                word, value, _ = mw[0]
                c.add(section="total", field_key="total_geral", label="Total Geral", value=value, page=row.page,
                      bbox=(word.x0, word.top, word.x1, word.bottom))
                break
        if not any(v.field_key == "faturamento.mes" for v in c.values):
            raise LayoutNotRecognized("nenhum mês de faturamento encontrado (parser " + PARSER_VERSION + ")")
        return ParseResult(doc_type=self.DOC_TYPE, parser_version=PARSER_VERSION, cnpj=cls.cnpj,
                           competence=cls.competence, pages=pages, values=c.values)
