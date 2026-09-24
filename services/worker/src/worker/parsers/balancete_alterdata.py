"""Parser do Balancete Analítico (Alterdata)."""
import re

from worker.classify import classify
from worker.errors import LayoutNotRecognized
from worker.models import DocType, ParseResult, Row
from worker.parsers.base import ValueCollector, money_words, require_anchor

PARSER_VERSION = "balancete-alterdata-1.0.0"

COLUMNS = ["saldo_anterior", "debito", "credito", "saldo_atual"]
CODE = re.compile(r"\[(\d+)\]")
END_OF_ACCOUNTS = "Análise do Balancete"
PERIOD_SUMMARY = [
    ("Receita", "periodo.receita", "Receita do período"),
    ("Despesa/Custo", "periodo.despesa_custo", "Despesa/custo do período"),
    ("Lucro", "periodo.lucro", "Lucro do período"),
]


class BalanceteAlterdataParser:
    DOC_TYPE = DocType.BALANCETE_ALTERDATA
    PARSER_VERSION = PARSER_VERSION

    def parse(self, rows: list[Row], pages: int) -> ParseResult:
        cls = classify(rows, DocType.BALANCETE_ALTERDATA)
        if not cls.cnpj or not cls.competence:
            raise LayoutNotRecognized("CNPJ ou período ausente (parser " + PARSER_VERSION + ")")
        require_anchor(rows, "Descrição Saldo Anterior Débito Crédito Saldo Atual", PARSER_VERSION)
        c = ValueCollector(cls.competence)

        account_rows = []
        in_period = False
        for row in rows:
            text = row.text
            if text.startswith(END_OF_ACCOUNTS):
                break
            m = CODE.search(text)
            if m and len(money_words(row)) == 4:
                account_rows.append((row, m.group(1)))

        if not account_rows:
            raise LayoutNotRecognized("nenhuma conta encontrada (parser " + PARSER_VERSION + ")")

        # Nível hierárquico pela indentação (posições x distintas da descrição).
        indents = sorted({round(r.words[0].x0) for r, _ in account_rows})
        for row, code in account_rows:
            level = indents.index(round(row.words[0].x0)) + 1
            desc_words = []
            for w in row.words:
                if CODE.fullmatch(w.text):
                    break
                desc_words.append(w.text)
            label = " ".join(desc_words).rstrip("-").strip()
            section = "grupo" if label == label.upper() else "analitica"
            section = section + ".nivel" + str(level)
            for (w, value, nature), col in zip(money_words(row), COLUMNS):
                c.add(section=section, field_key="conta." + code, label=label, value=value,
                      nature=nature, page=row.page, bbox=w.bbox, account_code=code, column=col)

        for row in rows:
            text = row.text
            if text.startswith("Valores do Período"):
                in_period = True
                continue
            if not in_period:
                continue
            mw = money_words(row)
            if not mw:
                continue
            for prefix, key, label in PERIOD_SUMMARY:
                if text.startswith(prefix) and c.find(key) is None:
                    w, value, nature = mw[-1]
                    c.add(section="periodo", field_key=key, label=label, value=value, nature=nature,
                          page=row.page, bbox=w.bbox)
                    break

        return ParseResult(
            doc_type=DocType.BALANCETE_ALTERDATA, parser_version=PARSER_VERSION, cnpj=cls.cnpj,
            competence=cls.competence, pages=pages, values=c.values,
        )
