"""Parser do "Resumo Geral" da folha (Alterdata)."""
import re
from decimal import Decimal

from worker.classify import classify
from worker.errors import LayoutNotRecognized
from worker.models import DocType, ParseResult, Row
from worker.parsers.base import ValueCollector, money_words, require_anchor, slug
from worker.pdf.numbers import is_money, parse_money

PARSER_VERSION = "folha-alterdata-1.0.0"

COLUMNS = ["ativos", "demitidos", "afastados", "total"]
RUBRICA = re.compile(r"\d\d\d")

TOTAIS = [
    ("TOTAL DE ADICIONAIS", "total_adicionais"),
    ("TOTAL DE DESCONTOS", "total_descontos"),
    ("TOTAL LÍQUIDO A PAGAR", "total_liquido"),
    ("TOTAL LÍQUIDO MÊS ANTERIOR", "liquido_mes_anterior_ferias"),
    ("TOTAL LÍQUIDO MÊS SEGUINTE", "liquido_mes_seguinte_ferias"),
]

# Rótulos da página 2 com chave canônica (usada pela conciliação).
KNOWN_KEYS = {
    ("encargos", "Empregados"): "gps.empregados",
    ("encargos", "Sub-Total"): "gps.subtotal",
    ("encargos", "Total Líquido"): "gps.total_liquido",
    ("encargos", "Base de calc. FGTS sem 13º"): "fgts.base_sem_13",
    ("encargos", "FGTS sem 13º salário s/CS"): "fgts.sem_13",
    ("encargos", "Total FGTS apurado recibos s/CS"): "fgts.apurado",
    ("encargos", "IRRF Folha"): "darf.irrf_folha",
    ("encargos", "Total de Empréstimo no mês"): "credito_trabalhador.total_emprestimo",
    ("auxiliares", "Base Empregados"): "aux.base_empregados",
}

HEADER_MARKERS = ("Empresa :", "Endereço :", "Período:", "Tipo Processo", "R e s u m o")


class FolhaAlterdataParser:
    DOC_TYPE = DocType.FOLHA_ALTERDATA
    PARSER_VERSION = PARSER_VERSION

    def parse(self, rows: list[Row], pages: int) -> ParseResult:
        cls = classify(rows, DocType.FOLHA_ALTERDATA)
        if not cls.cnpj or not cls.competence:
            raise LayoutNotRecognized("CNPJ ou período ausente (parser " + PARSER_VERSION + ")")
        c = ValueCollector(cls.competence)

        start = require_anchor(rows, "ADICIONAIS / DESCONTOS", PARSER_VERSION)
        for anchor, _ in TOTAIS[:3]:
            require_anchor(rows, anchor, PARSER_VERSION, start)
        end = require_anchor(rows, "TOTAL DE FUNCIONÁRIOS", PARSER_VERSION, start)
        encargos = require_anchor(rows, "BASES DE CÁLCULO - GFIP", PARSER_VERSION, end)

        self._resumo(rows[start + 1:end + 1], c)
        self._encargos(rows[encargos - 1:], c)

        if c.find("total_adicionais", "total") is None or c.find("fgts.apurado") is None:
            raise LayoutNotRecognized("totais da folha ausentes (parser " + PARSER_VERSION + ")")
        return ParseResult(
            doc_type=DocType.FOLHA_ALTERDATA, parser_version=PARSER_VERSION, cnpj=cls.cnpj,
            competence=cls.competence, pages=pages, values=c.values,
        )

    def _resumo(self, rows: list[Row], c: ValueCollector) -> None:
        section = "adicionais"
        for row in rows:
            text = row.text
            total_key = next((k for a, k in TOTAIS if text.startswith(a)), None)
            if total_key:
                self._columns(row, "totais", total_key, text.split("  ")[0], None, c)
                if total_key == "total_adicionais":
                    section = "descontos"
                continue
            if text.startswith("TOTAL DE FUNCIONÁRIOS"):
                ints = [w for w in row.words if re.fullmatch(r"\d+", w.text)]
                for w, col in zip(ints, COLUMNS):
                    c.add(section="totais", field_key="total_funcionarios", label="Total de funcionários",
                          value=Decimal(w.text), page=row.page, bbox=w.bbox, column=col)
                continue
            first = row.words[0].text
            if RUBRICA.fullmatch(first) and len(money_words(row)) == 4:
                label = " ".join(w.text for w in row.words[1:] if not is_money(w.text))
                self._columns(row, section, "rubrica." + first, label, first, c)

    def _columns(self, row: Row, section: str, key: str, label: str, code: str | None, c: ValueCollector) -> None:
        mw = money_words(row)
        if len(mw) != 4:
            raise LayoutNotRecognized("linha da folha com " + str(len(mw)) + " colunas (parser " + PARSER_VERSION + ")")
        label = " ".join(w.text for w in row.words if not is_money(w.text)) if code is None else label
        for (w, value, _), col in zip(mw, COLUMNS):
            c.add(section=section, field_key=key, label=label, value=value, page=row.page,
                  bbox=w.bbox, column=col, account_code=code)

    def _encargos(self, rows: list[Row], c: ValueCollector) -> None:
        section = "encargos"
        for row in rows:
            text = row.text
            if any(m in text for m in HEADER_MARKERS):
                continue
            if "INFORMAÇÕES AUXILIARES" in text:
                section = "auxiliares"
                continue
            if "APOSENTADORIA ESPECIAL" in text:
                section = "aposentadoria_especial"
                continue
            label_acc: list[str] = []
            for w in row.words:
                if is_money(w.text):
                    value, _ = parse_money(w.text)
                    label = " ".join(label_acc).strip().rstrip(":").strip() or section
                    key = KNOWN_KEYS.get((section, label))
                    if key is None or c.find(key) is not None:
                        key = section + "." + slug(label)
                    c.add(section=section, field_key=key, label=label, value=value,
                          page=row.page, bbox=w.bbox)
                    label_acc = []
                else:
                    label_acc.append(w.text)
