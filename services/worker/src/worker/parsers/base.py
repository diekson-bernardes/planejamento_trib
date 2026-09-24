"""Contrato dos parsers e utilitários comuns."""
import re
import unicodedata
from decimal import Decimal
from typing import Protocol

from worker.errors import LayoutNotRecognized
from worker.models import DocType, ExtractedValue, ParseResult, Row, Word
from worker.pdf.numbers import is_money, parse_money


class Parser(Protocol):
    DOC_TYPE: DocType
    PARSER_VERSION: str

    def parse(self, rows: list[Row], pages: int) -> ParseResult: ...


def require_anchor(rows: list[Row], anchor: str, parser_version: str, start: int = 0) -> int:
    for i in range(start, len(rows)):
        if anchor in rows[i].text:
            return i
    raise LayoutNotRecognized(
        "âncora ausente: " + repr(anchor) + " (parser " + parser_version + ")"
    )


def find_anchor(rows: list[Row], anchor: str, start: int = 0, stop: int | None = None) -> int | None:
    for i in range(start, len(rows) if stop is None else stop):
        if anchor in rows[i].text:
            return i
    return None


def money_words(row: Row) -> list[tuple[Word, Decimal, str | None]]:
    out = []
    for w in row.words:
        if is_money(w.text):
            value, nature = parse_money(w.text)
            out.append((w, value, nature))
    return out


def label_words(row: Row) -> str:
    """Texto da linha sem os tokens monetários."""
    return " ".join(w.text for w in row.words if not is_money(w.text))


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "campo"


class ValueCollector:
    """Acumula valores extraídos atribuindo ordinais sequenciais e estáveis."""

    def __init__(self, competence: str):
        self.competence = competence
        self.values: list[ExtractedValue] = []

    def add(
        self,
        *,
        section: str,
        field_key: str,
        label: str,
        value: Decimal,
        page: int,
        bbox: tuple[float, float, float, float],
        nature: str | None = None,
        account_code: str | None = None,
        column: str | None = None,
        competence: str | None = None,
    ) -> ExtractedValue:
        ev = ExtractedValue(
            ordinal=len(self.values),
            section=section,
            field_key=field_key,
            label=label,
            account_code=account_code,
            column=column,
            competence=competence or self.competence,
            value=value,
            nature=nature,
            page=page,
            bbox=tuple(round(c, 2) for c in bbox),
        )
        self.values.append(ev)
        return ev

    def find(self, field_key: str, column: str | None = None, section: str | None = None) -> ExtractedValue | None:
        for v in self.values:
            if v.field_key == field_key and (column is None or v.column == column) and (
                section is None or v.section == section
            ):
                return v
        return None
