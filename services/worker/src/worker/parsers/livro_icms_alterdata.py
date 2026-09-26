"""Parser do Registro de Apuração do ICMS (Alterdata): entradas e saídas por CFOP, subtotais por origem e totais."""
import re

from worker.classify import classify
from worker.errors import LayoutNotRecognized
from worker.models import DocType, ParseResult, Row
from worker.parsers.base import ValueCollector, money_words, require_anchor

PARSER_VERSION = "livro-icms-alterdata-1.0.0"

COLUMNS = ("valor_contabil", "base_calculo", "imposto", "isentas_nao_tributadas", "outras")
CFOP = re.compile(r"^(\d{4})\s")
SUBTOTAL = re.compile(r"^(\d\.00)\s")
SECTIONS = (("E N T R A D A S", "entradas"), ("S A Í D A S", "saidas"))


class LivroIcmsAlterdataParser:
    DOC_TYPE = DocType.LIVRO_ICMS_ALTERDATA
    PARSER_VERSION = PARSER_VERSION

    def parse(self, rows: list[Row], pages: int) -> ParseResult:
        cls = classify(rows, DocType.LIVRO_ICMS_ALTERDATA)
        if not cls.cnpj or not cls.competence:
            raise LayoutNotRecognized("CNPJ ou período ausente (parser " + PARSER_VERSION + ")")
        require_anchor(rows, "E N T R A D A S", PARSER_VERSION)
        require_anchor(rows, "S A Í D A S", PARSER_VERSION)
        c = ValueCollector(cls.competence)

        section = None
        pending_subtotal: tuple[str, str] | None = None     # "2.00 De Outros" + "Estados <valores>" na linha seguinte
        for row in rows:
            text = row.text.strip()
            header = next((key for anchor, key in SECTIONS if text.startswith(anchor)), None)
            if header:
                section, pending_subtotal = header, None
                continue
            if section is None or row.page != 1:
                continue
            mw = money_words(row)
            m_cfop = CFOP.match(text)
            m_sub = SUBTOTAL.match(text)
            if m_cfop and len(mw) == len(COLUMNS):
                self._add(c, row, mw, section, "cfop." + m_cfop.group(1), "CFOP " + m_cfop.group(1))
            elif m_sub and len(mw) == len(COLUMNS):
                label = text[: text.index(str(mw[0][0].text))].strip()
                self._add(c, row, mw, section, "subtotal." + m_sub.group(1), label)
            elif m_sub and not mw:
                pending_subtotal = (m_sub.group(1), text)
            elif pending_subtotal and len(mw) == len(COLUMNS):
                code, first = pending_subtotal
                label = (first + " " + text[: text.index(str(mw[0][0].text))]).strip()
                self._add(c, row, mw, section, "subtotal." + code, label)
                pending_subtotal = None
            elif text.startswith("T O T A I S") and len(mw) == len(COLUMNS):
                self._add(c, row, mw, section, "total", "Totais das " + section)
                section = None
        if not any(v.field_key.startswith("cfop.") for v in c.values):
            raise LayoutNotRecognized("nenhuma linha de CFOP encontrada (parser " + PARSER_VERSION + ")")
        return ParseResult(doc_type=self.DOC_TYPE, parser_version=PARSER_VERSION, cnpj=cls.cnpj,
                           competence=cls.competence, pages=pages, values=c.values)

    @staticmethod
    def _add(c: ValueCollector, row: Row, mw, section: str, field_key: str, label: str) -> None:
        for column, (word, value, _nature) in zip(COLUMNS, mw):
            c.add(section=section, field_key=field_key, label=label, value=value, page=row.page,
                  bbox=(word.x0, word.top, word.x1, word.bottom), column=column)
