"""Números e identificadores no formato brasileiro."""
import re
from datetime import date
from decimal import Decimal

# Quantificadores escritos por extenso: \d\d?\d? = 1 a 3 dígitos.
MONEY = re.compile(r"\**(-?\d\d?\d?(?:\.\d\d\d)*,\d\d)([DC])?")
GLUED = re.compile(r"(\d\d?\d?(?:\.\d\d\d)*,\d\d)(\d\d/\d\d\d\d)")  # "92.916,6302/2025"
COMPETENCE = re.compile(r"(\d\d)/(\d\d\d\d)")
DATE = re.compile(r"(\d\d)/(\d\d)/(\d\d\d\d)")
CNPJ_DIGITS = re.compile(r"\d\d\.?\d\d\d\.?\d\d\d/?\d\d\d\d-?\d\d")


def is_money(token: str) -> bool:
    return MONEY.fullmatch(token.strip()) is not None


def parse_money(token: str) -> tuple[Decimal, str | None]:
    m = MONEY.fullmatch(token.strip())
    if not m:
        raise ValueError("valor monetário inválido: " + repr(token))
    value = Decimal(m.group(1).replace(".", "").replace(",", "."))
    return value, m.group(2)  # natureza 'D' | 'C' | None


def signed(value: Decimal, nature: str | None) -> Decimal:
    """Saldo com sinal: devedor positivo, credor negativo."""
    return -value if nature == "C" else value


def unglue(text: str) -> str:
    return GLUED.sub(r"\1 \2", text)


def split_glued(token: str) -> tuple[str, str | None]:
    """Separa '92.916,6302/2025' em ('92.916,63', '02/2025')."""
    m = GLUED.fullmatch(token)
    if m:
        return m.group(1), m.group(2)
    return token, None


def competence_from_mm_yyyy(token: str) -> str:
    m = COMPETENCE.fullmatch(token)
    if not m:
        raise ValueError("competência inválida: " + repr(token))
    return m.group(2) + "-" + m.group(1)


def parse_date(token: str) -> date:
    m = DATE.search(token)
    if not m:
        raise ValueError("data inválida: " + repr(token))
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))


def normalize_cnpj(text: str) -> str | None:
    m = CNPJ_DIGITS.search(text)
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(0))
    return digits if len(digits) == 14 else None


def cnpj_is_valid(cnpj: str) -> bool:
    if not re.fullmatch(r"\d{14}", cnpj) or len(set(cnpj)) == 1:
        return False
    nums = [int(c) for c in cnpj]
    for size in (12, 13):
        weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-size:]
        total = sum(n * w for n, w in zip(nums[:size], weights))
        check = 0 if total % 11 < 2 else 11 - total % 11
        if nums[size] != check:
            return False
    return True
