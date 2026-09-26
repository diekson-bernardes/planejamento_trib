"""Classificação determinística por âncoras de cabeçalho da página 1."""
from dataclasses import dataclass
from datetime import date

from worker.errors import Unclassified
from worker.models import DocType, Row
from worker.pdf.numbers import DATE, normalize_cnpj, parse_date

# (tipo, âncoras que precisam aparecer todas na página 1, âncora da linha do período)
ANCHORS: list[tuple[DocType, tuple[str, ...], str]] = [
    (DocType.PGDAS_D, ("Programa Gerador do Documento de Arrecadação",), "Período de Apuração"),
    (DocType.FOLHA_ALTERDATA, ("ADICIONAIS / DESCONTOS",), "Período:"),
    (DocType.DRE_ALTERDATA, ("Demonstração do Resultado do Exercício",), "Demonstração do Resultado"),
    (DocType.BALANCETE_ALTERDATA, ("Balancete Analítico",), "Balancete Analítico"),
    (DocType.LIVRO_ICMS_ALTERDATA, ("R E G I S T R O D E A P U R A Ç Ã O D O I C M S",), "Mês ou Período/Ano"),
]


@dataclass(frozen=True)
class Classification:
    doc_type: DocType
    cnpj: str | None
    period_start: date | None
    period_end: date | None

    @property
    def competence(self) -> str | None:
        """Competência = mês do fim do período (YYYY-MM)."""
        return self.period_end.strftime("%Y-%m") if self.period_end else None

    @property
    def monthly(self) -> bool:
        return bool(
            self.period_start
            and self.period_end
            and (self.period_start.year, self.period_start.month)
            == (self.period_end.year, self.period_end.month)
        )


def _page_text(rows: list[Row], page: int = 1) -> str:
    return "\n".join(r.text for r in rows if r.page == page)


def detect_type(rows: list[Row]) -> DocType:
    text = _page_text(rows)
    for doc_type, anchors, _ in ANCHORS:
        if all(a in text for a in anchors):
            return doc_type
    raise Unclassified("nenhuma âncora de cabeçalho conhecida encontrada")


def classify(rows: list[Row], forced: DocType | None = None) -> Classification:
    doc_type = forced or detect_type(rows)
    period_anchor = next(a for t, _, a in ANCHORS if t == doc_type)
    page1 = [r for r in rows if r.page == 1]

    cnpj = None
    for r in page1:
        if "CNPJ" in r.text.replace(".", ""):   # "CNPJ" ou "C.N.P.J." (Livro de Apuração)
            cnpj = normalize_cnpj(r.text)
            if cnpj:
                break

    start = end = None
    for r in page1:
        if period_anchor in r.text:
            dates = DATE.findall(r.text)
            if len(dates) >= 2:
                start = parse_date("/".join(dates[0]))
                end = parse_date("/".join(dates[1]))
            break

    return Classification(doc_type=doc_type, cnpj=cnpj, period_start=start, period_end=end)
