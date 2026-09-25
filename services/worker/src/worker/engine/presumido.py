"""Lucro Presumido: IRPJ/CSLL trimestrais por presunção (com LC 224/2025) e PIS/Cofins cumulativo mensal."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from worker.engine.assumptions import Assumptions, comp_scope
from worker.engine.memory import D, ZERO, Line, brl, money, pct
from worker.engine.payroll import charges
from worker.engine.rules import MissingRule, RuleSet
from worker.engine.snapshot import SnapshotView


def quarter_of(comp: str) -> str:
    return f"{comp[:4]}-T{(int(comp[5:7]) - 1) // 3 + 1}"


def group_quarters(comps: list[str]) -> dict:
    out: dict = {}
    for c in comps:
        out.setdefault(quarter_of(c), []).append(c)
    return out


@dataclass(frozen=True)
class QuarterInput:
    period: str                        # "2026-T3"
    months: int                        # meses considerados (completos)
    revenue_by_class: dict             # classe → receita do trimestre
    outras_receitas: Decimal           # somadas integralmente
    excess: Decimal = ZERO             # receita do trimestre acima do limite da LC 224
    irpj_majorado: bool = False
    csll_majorado: bool = False
    partial: bool = False
    origin: dict | None = None


def quarter_lines(q: QuarterInput, rules: RuleSet) -> list[Line]:
    """IRPJ, adicional e CSLL de um trimestre (função pura — usada nos casos dourados)."""
    pr = rules.presumido
    fator = D(pr["lc224"]["fator"])
    total_rev = sum(q.revenue_by_class.values(), ZERO)
    verified = rules.verified.get("presumido", False)
    origin = q.origin or {"source": "calculo_trimestral", "period": q.period}
    lines = []
    bases = {"irpj": ZERO, "csll": ZERO}
    detail = {"irpj": [], "csll": []}
    for cls, rev in sorted(q.revenue_by_class.items()):
        if cls not in pr["classes"]:
            raise MissingRule(f"classe de presunção sem regra: {cls}")
        excess_cls = q.excess * rev / total_rev if total_rev else ZERO
        for tax in ("irpj", "csll"):
            p = D(pr["classes"][cls][tax])
            majorado = q.irpj_majorado if tax == "irpj" else q.csll_majorado
            base = rev * p + (excess_cls * p * (fator - 1) if majorado else ZERO)
            bases[tax] += base
            txt = f"{cls}: {brl(rev)} × {pct(p, 2)}"
            if majorado and excess_cls:
                txt += f" + excedente LC 224 {brl(excess_cls)} × {pct(p, 2)} × 10%"
            detail[tax].append(txt)
            lines.append(Line("PRESUMIDO", q.period, "base_presumida_" + tax, money(base), p, money(base),
                              txt, rules.ref("presumido", "classes", cls, tax), kind="informativo",
                              partial=q.partial, verified=verified, origin=origin))
    for tax in ("irpj", "csll"):
        bases[tax] += q.outras_receitas
    if q.outras_receitas:
        lines.append(Line("PRESUMIDO", q.period, "outras_receitas", money(q.outras_receitas), ZERO, money(q.outras_receitas),
                          "outras receitas somadas integralmente às bases", rules.ref("presumido", "outras_receitas"),
                          kind="informativo", partial=q.partial, verified=verified, origin=q.origin or {}))
    irpj_rate, csll_rate, add_rate = D(pr["irpj"]), D(pr["csll"]), D(pr["adicional_irpj"])
    limite = D(pr["adicional_limite_mensal"]) * q.months
    b_irpj, b_csll = money(bases["irpj"]), money(bases["csll"])
    lines.append(Line("PRESUMIDO", q.period, "irpj", b_irpj, irpj_rate, money(b_irpj * irpj_rate),
                      f"base {brl(b_irpj)} ({' + '.join(detail['irpj'])}) × 15%", rules.ref("presumido", "irpj"),
                      partial=q.partial, verified=verified, origin=origin))
    add_base = max(ZERO, b_irpj - limite)
    lines.append(Line("PRESUMIDO", q.period, "adicional_irpj", add_base, add_rate, money(add_base * add_rate),
                      f"(base {brl(b_irpj)} − {brl(limite)} [R$ 20.000 × {q.months} mês(es)]) × 10%",
                      rules.ref("presumido", "adicional_irpj"), partial=q.partial, verified=verified, origin=origin))
    lines.append(Line("PRESUMIDO", q.period, "csll", b_csll, csll_rate, money(b_csll * csll_rate),
                      f"base {brl(b_csll)} ({' + '.join(detail['csll'])}) × 9%", rules.ref("presumido", "csll"),
                      partial=q.partial, verified=verified, origin=origin))
    return lines


def month_pis_cofins(comp: str, base: Decimal | dict, rules: RuleSet, formula: str | dict,
                     origin: dict | None = None) -> list[Line]:
    """PIS/Cofins cumulativos do mês. `base`/`formula` podem ser por tributo (monofásico só de PIS ou só de Cofins).
    A base nunca fica negativa: exclusão maior que a receita zera o tributo, não reduz o total."""
    pr = rules.presumido
    verified = rules.verified.get("presumido", False)
    out = []
    for tax, key in (("pis", "pis_cumulativo"), ("cofins", "cofins_cumulativo")):
        rate = D(pr[key])
        tax_base = max(ZERO, base[tax] if isinstance(base, dict) else base)
        tax_formula = formula[tax] if isinstance(formula, dict) else formula
        out.append(Line("PRESUMIDO", comp, tax, money(tax_base), rate, money(tax_base * rate),
                        f"{tax_formula} × {pct(rate, 2)}", rules.ref("presumido", key), origin=origin or {}, verified=verified))
    return out


def lc224_excess(view: SnapshotView, period: str, comps: list[str], quarter_revenue: Decimal, rules: RuleSet) -> Decimal:
    """Receita do trimestre acima do limite trimestral acumulado (A-002 do DEFINE)."""
    lc = rules.presumido["lc224"]
    q = int(period[-1])
    last = comps[-1]
    rba = view.value("PGDAS_D", last, "receita.rba", "total") or ZERO
    rpa = view.value("PGDAS_D", last, "receita.rpa", "total") or ZERO
    acumulada = rba + rpa
    limite = D(lc["limite_trimestral"]) * q
    return min(quarter_revenue, max(ZERO, acumulada - limite))


def calculate(comps: list[str], view: SnapshotView, a: Assumptions, rules: RuleSet) -> list[Line]:
    lc = rules.presumido["lc224"]
    lines: list[Line] = []
    for period, months in group_quarters(comps).items():
        revenue: dict = {}
        outras = ZERO
        sources: list = []
        for comp in months:
            receita_bruta = ZERO
            monofasica = {"pis": ZERO, "cofins": ZERO}
            for act in view.activities(comp):
                profile = a.profile(act.key)
                if profile is None:
                    raise MissingRule(f"atividade sem perfil confirmado: {act.description}")
                revenue[profile.presumido] = revenue.get(profile.presumido, ZERO) + act.receita
                receita_bruta += act.receita
                sources.append(act.origin)
                for tax in a.zeroed(act.key) & {"pis", "cofins"}:
                    monofasica[tax] += act.receita
            outras += a.decimal("outras_receitas", comp_scope(comp))
            exclusoes = a.decimal("pis_cofins_exclusoes", comp_scope(comp))
            lines += month_pis_cofins(
                comp, {t: receita_bruta - monofasica[t] - exclusoes for t in monofasica}, rules,
                {t: f"(receita bruta {brl(receita_bruta)} − monofásica {brl(monofasica[t])} − exclusões {brl(exclusoes)})"
                 for t in monofasica},
                a.origin("pis_cofins_exclusoes", comp_scope(comp)))
            for tax, key in (("icms", "icms_regime_normal"), ("iss", "iss_regime_normal")):
                value = a.decimal(key, comp_scope(comp))
                lines.append(Line("PRESUMIDO", comp, tax, value, ZERO, money(value), f"{tax.upper()} no regime normal — premissa",
                                  rules.ref("premissa", key), origin=a.origin(key, comp_scope(comp)), verified=False))
            lines += charges("PRESUMIDO", comp, view, a, rules)
        q_rev = sum(revenue.values(), ZERO)
        start = date(int(period[:4]), (int(period[-1]) - 1) * 3 + 1, 1)
        excess = lc224_excess(view, period, months, q_rev, rules)
        lines += quarter_lines(QuarterInput(
            period=period, months=len(months), revenue_by_class=revenue, outras_receitas=outras, excess=excess,
            irpj_majorado=start >= date.fromisoformat(lc["irpj_desde"]) and excess > 0,
            csll_majorado=start >= date.fromisoformat(lc["csll_desde"]) and excess > 0,
            partial=len(months) < 3,
            origin={"source": "calculo_trimestral", "period": period, "months": months, "receitas": sources,
                    "outras_receitas": [a.origin("outras_receitas", comp_scope(c)) for c in months]},
        ), rules)
        if excess > 0:
            lines.append(Line("PRESUMIDO", period, "lc224_excedente", money(excess), D(lc["fator"]), money(excess),
                              f"receita acima do limite trimestral acumulado (R$ 1,25 mi × T{period[-1]})",
                              rules.ref("presumido", "lc224"), kind="informativo", partial=len(months) < 3, verified=False))
    return lines
