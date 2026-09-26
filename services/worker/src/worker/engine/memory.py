"""Memória de cálculo: cada valor do motor vira uma `Line` auditável."""
import hashlib
import json
from dataclasses import asdict, dataclass, field
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0")

REGIMES = ("SIMPLES", "PRESUMIDO", "REAL")
HIBRIDO = "SIMPLES_HIBRIDO"          # 2027+: Simples com CBS/IBS fora do DAS (regime regular)


def regimes_for(rules) -> tuple:
    """Regimes calculados no exercício das regras: os três de sempre + o Simples híbrido quando previsto."""
    return REGIMES + ((HIBRIDO,) if rules.simples.get("hibrido") else ())


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def D(value) -> Decimal:
    """Converte string/número/Decimal em Decimal sem passar por float."""
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return ZERO
    return Decimal(str(value))


def brl(value: Decimal) -> str:
    q = money(value)
    sign = "-" if q < 0 else ""
    integer, _, cents = f"{abs(q):.2f}".partition(".")
    groups = []
    while integer:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    return sign + ".".join(groups) + "," + cents


def pct(rate: Decimal, places: int = 4) -> str:
    return f"{(rate * 100):.{places}f}".replace(".", ",") + "%"


@dataclass(frozen=True)
class Line:
    regime: str            # SIMPLES | PRESUMIDO | REAL
    period: str            # "2026-08" (mensal) ou "2026-T3" (trimestral)
    tax: str               # irpj, adicional_irpj, csll, pis, cofins, cpp, rat, terceiros, icms, iss, ipi, ...
    base: Decimal
    rate: Decimal
    amount: Decimal
    formula: str
    rule_ref: str
    kind: str = "tributo"  # tributo (entra no total) | reclassificacao | informativo
    origin: dict = field(default_factory=dict)
    activity: str | None = None
    partial: bool = False
    verified: bool = True  # False quando a regra aplicada não foi conferida na fonte primária


def canonical_hash(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def line_dict(line: Line) -> dict:
    d = asdict(line)
    for k in ("base", "rate", "amount"):
        d[k] = str(d[k])
    return d


def lines_hash(lines: list[Line]) -> str:
    return canonical_hash([line_dict(line) for line in lines])
