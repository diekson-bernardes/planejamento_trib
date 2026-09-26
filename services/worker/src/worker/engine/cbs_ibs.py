"""CBS e IBS (Reforma Tributária, exercícios a partir de 2027): débito sobre a receita, crédito financeiro sobre a
base de créditos e saldo credor transportado — substituem PIS/Cofins quando `rules.consumo` existe."""
from decimal import Decimal

from worker.engine.assumptions import Assumptions, comp_scope
from worker.engine.memory import ZERO, Line, brl, money, pct
from worker.engine.rules import MissingRule, RuleSet

TAXES = ("cbs", "ibs")


def rates(a: Assumptions, rules: RuleSet, comp: str) -> dict:
    """Alíquotas confirmadas pelo escritório (premissas sem padrão). Ausente → regime "não calculado"."""
    out = {}
    for tax in TAXES:
        key = rules.consumo["tributos"][tax]["premissa_aliquota"]
        if a.raw(key) is None:
            raise MissingRule(f"{comp}: alíquota de {tax.upper()} de {comp[:4]} não confirmada (premissa {key})")
        out[tax] = a.decimal(key)
    return out


def month_lines(regime: str, comp: str, receita: Decimal, exempt: Decimal, a: Assumptions, rules: RuleSet,
                saldo: dict, icms_iss: Decimal = ZERO) -> list[Line]:
    """Débito = (receita − isenta/monofásica − ICMS/ISS − exclusões) × alíquota; crédito = base de créditos × alíquota
    + saldo. `icms_iss` é o ICMS/ISS do próprio regime no mês (fora da base: LC 214, art. 12, § 2º).

    `saldo` (tributo → saldo credor) é atualizado: o excedente de crédito passa ao mês seguinte."""
    scope = comp_scope(comp)
    exclusoes = a.decimal("pis_cofins_exclusoes", scope)     # demais exclusões informadas pelo escritório
    creditos = a.decimal("reforma.creditos_base", scope)
    base = max(ZERO, receita - exempt - icms_iss - exclusoes)
    verified = rules.verified.get("consumo", False)
    lines = []
    for tax, rate in rates(a, rules, comp).items():
        debito = base * rate
        anterior = saldo.get(tax, ZERO)
        credito = creditos * rate + anterior
        devido = max(ZERO, debito - credito)
        saldo[tax] = max(ZERO, credito - debito)
        key = rules.consumo["tributos"][tax]["premissa_aliquota"]
        lines.append(Line(
            regime, comp, tax, money(base), rate, money(devido),
            f"(receita {brl(receita)} − isenta/monofásica {brl(exempt)} − ICMS/ISS {brl(icms_iss)}"
            f" − exclusões {brl(exclusoes)}) × {pct(rate, 2)}"
            f" − créditos {brl(creditos)} × {pct(rate, 2)}"
            + (f" − saldo credor anterior {brl(anterior)}" if anterior else "")
            + (f" [saldo credor {brl(saldo[tax])} transportado]" if saldo[tax] else ""),
            rules.ref("consumo", tax),
            origin={"aliquota": a.origin(key), "creditos": a.origin("reforma.creditos_base", scope),
                    "exclusoes": a.origin("pis_cofins_exclusoes", scope)},
            verified=verified,
        ))
    return lines
