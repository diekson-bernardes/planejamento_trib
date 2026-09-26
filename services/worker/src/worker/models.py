"""Modelos compartilhados entre layout, parsers, validações e conciliação."""
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


class DocType(StrEnum):
    PGDAS_D = "PGDAS_D"
    FOLHA_ALTERDATA = "FOLHA_ALTERDATA"
    DRE_ALTERDATA = "DRE_ALTERDATA"
    BALANCETE_ALTERDATA = "BALANCETE_ALTERDATA"
    LIVRO_ICMS_ALTERDATA = "LIVRO_ICMS_ALTERDATA"     # opcional: não entra na definição de competência completa


@dataclass(frozen=True)
class Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x0, self.top, self.x1, self.bottom)


@dataclass(frozen=True)
class Row:
    page: int  # base 1
    words: tuple[Word, ...]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def top(self) -> float:
        return min(w.top for w in self.words)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (
            min(w.x0 for w in self.words),
            min(w.top for w in self.words),
            max(w.x1 for w in self.words),
            max(w.bottom for w in self.words),
        )


class ExtractedValue(BaseModel):
    ordinal: int
    section: str
    field_key: str
    label: str
    account_code: str | None = None
    column: str | None = None
    competence: str  # "YYYY-MM"
    value: Decimal
    nature: str | None = None  # "D" | "C"
    page: int
    bbox: tuple[float, float, float, float]


class ParseResult(BaseModel):
    doc_type: DocType
    parser_version: str
    cnpj: str
    competence: str
    pages: int
    values: list[ExtractedValue]


class ValidationResult(BaseModel):
    rule: str
    status: str  # "pass" | "fail"
    expected: Decimal | None = None
    actual: Decimal | None = None
    diff: Decimal | None = None
    detail: str | None = None


class ReconciliationResult(BaseModel):
    competence: str  # "YYYY-MM"
    rule: str  # R1..R6
    description: str
    left_label: str
    left_value: Decimal | None
    right_label: str
    right_value: Decimal | None
    diff: Decimal | None
    tolerance: Decimal
    status: str  # "ok" | "divergent" | "missing_source"
    details: dict = {}
