"""Lucro Real: lucro ajustado trimestral (com reclassificação do lucro da DRE) e PIS/Cofins não cumulativo."""
from dataclasses import dataclass
from decimal import Decimal

from worker.engine import cbs_ibs
from worker.engine.assumptions import Assumptions, comp_scope
from worker.engine.memory import D, ZERO, Line, brl, money, pct
from worker.engine.payroll import charges
from worker.engine.presumido import group_quarters
from worker.engine.rules import MissingRule, RuleSet
from worker.engine.snapshot import SnapshotView


@dataclass(frozen=True)
class QuarterProfit:
    period: str
    months: int
    lucro_antes: Decimal        # lucro antes de IRPJ/CSLL já reclassificado para o regime
    adicoes: Decimal
    exclusoes: Decimal
    saldo_prejuizo: Decimal
    saldo_base_negativa: Decimal
    partial: bool = False
    origin: dict | None = None


@dataclass(frozen=True)
class QuarterOutcome:
    lines: list
    saldo_prejuizo: Decimal
    saldo_base_negativa: Decimal


def quarter_lines(q: QuarterProfit, rules: RuleSet) -> QuarterOutcome:
    """IRPJ, adicional e CSLL de um trimestre com trava de 30% (função pura — usada nos casos dourados)."""
    rr = rules.real
    verified = rules.verified.get("real", False)
    trava = D(rr["trava_compensacao"])
    origin = q.origin or {"source": "calculo_trimestral", "period": q.period}
    ajustado = q.lucro_antes + q.adicoes - q.exclusoes
    lines = [Line("REAL", q.period, "lucro_ajustado", money(ajustado), ZERO, money(ajustado),
                  f"lucro antes de IRPJ/CSLL {brl(q.lucro_antes)} + adições {brl(q.adicoes)} − exclusões {brl(q.exclusoes)}",
                  rules.ref("real", "lucro_ajustado"), kind="informativo", partial=q.partial, verified=verified)]
    out = {}
    for tax, saldo in (("irpj", q.saldo_prejuizo), ("csll", q.saldo_base_negativa)):
        if ajustado > 0:
            comp = min(saldo, money(ajustado * trava))
            base = ajustado - comp
            novo_saldo = saldo - comp
            label = "prejuízo fiscal" if tax == "irpj" else "base negativa de CSLL"
            lines.append(Line("REAL", q.period, "compensacao_" + tax, money(comp), trava, money(comp),
                              f"mín(saldo de {label} {brl(saldo)}; 30% × {brl(ajustado)}) = {brl(comp)}; saldo final {brl(novo_saldo)}",
                              rules.ref("real", "trava_compensacao"), kind="informativo", partial=q.partial, verified=verified))
        else:
            base = ZERO
            novo_saldo = saldo - ajustado   # prejuízo do período aumenta o saldo
            lines.append(Line("REAL", q.period, "prejuizo_gerado_" + tax, money(-ajustado), ZERO, money(-ajustado),
                              f"resultado ajustado negativo: saldo passa a {brl(novo_saldo)}",
                              rules.ref("real", "prejuizo"), kind="informativo", partial=q.partial, verified=verified))
        out[tax] = (money(base), novo_saldo)
    b_irpj, b_csll = out["irpj"][0], out["csll"][0]
    irpj_rate, add_rate, csll_rate = D(rr["irpj"]), D(rr["adicional_irpj"]), D(rr["csll"])
    limite = D(rr["adicional_limite_mensal"]) * q.months
    add_base = max(ZERO, b_irpj - limite)
    lines += [
        Line("REAL", q.period, "irpj", b_irpj, irpj_rate, money(b_irpj * irpj_rate), f"lucro real {brl(b_irpj)} × 15%",
             rules.ref("real", "irpj"), partial=q.partial, verified=verified, origin=origin),
        Line("REAL", q.period, "adicional_irpj", add_base, add_rate, money(add_base * add_rate),
             f"(lucro real {brl(b_irpj)} − {brl(limite)} [R$ 20.000 × {q.months} mês(es)]) × 10%",
             rules.ref("real", "adicional_irpj"), partial=q.partial, verified=verified, origin=origin),
        Line("REAL", q.period, "csll", b_csll, csll_rate, money(b_csll * csll_rate), f"base de CSLL {brl(b_csll)} × 9%",
             rules.ref("real", "csll"), partial=q.partial, verified=verified, origin=origin),
    ]
    return QuarterOutcome(lines, out["irpj"][1], out["csll"][1])


def _lucro_dre(view: SnapshotView, comp: str) -> tuple[Decimal, dict]:
    v = view.get("DRE_ALTERDATA", comp, "resultado.lucro_liquido")
    if v is None:
        raise MissingRule(f"{comp}: DRE sem resultado do exercício")
    value = D(v["value"])
    if "preju" in (v.get("label") or "").lower() or v.get("nature") == "D":
        value = -value
    return value, view.origin(v)


def _despesa_simples(view: SnapshotView, comp: str) -> tuple[Decimal, dict]:
    for v in view.dre_accounts(comp):
        if "simples nacional" in (v.get("label") or "").lower():
            return D(v["value"]), view.origin(v)
    v = view.get("PGDAS_D", comp, "tributo.total", "total", "2.8.total_declarado")
    return (D(v["value"]) if v else ZERO), view.origin(v)


def _receita_mes(view: SnapshotView, a: Assumptions, comp: str) -> tuple[Decimal, Decimal]:
    """Receita do mês e parcela monofásica (atividades com PIS ou Cofins zerado) — base de CBS/IBS."""
    receita = exempt = ZERO
    for act in view.activities(comp):
        if a.profile(act.key) is None:
            raise MissingRule(f"atividade sem perfil confirmado: {act.description}")
        receita += act.receita
        if {"pis", "cofins"} & a.zeroed(act.key):
            exempt += act.receita
    return receita, exempt


def month_pis_cofins(comp: str, view: SnapshotView, a: Assumptions, rules: RuleSet,
                     saldo_credor: dict | None = None) -> list[Line]:
    """PIS/Cofins do mês no Real. `saldo_credor` (tributo → saldo) é atualizado: crédito excedente passa ao mês seguinte."""
    rr = rules.real
    verified = rules.verified.get("real", False)
    saldo_credor = {} if saldo_credor is None else saldo_credor
    # receitas por tributo: uma atividade pode ter só PIS ou só Cofins zerado (monofásico parcial)
    nc_rev = {"pis": ZERO, "cofins": ZERO}
    cum_rev = {"pis": ZERO, "cofins": ZERO}
    for act in view.activities(comp):
        profile = a.profile(act.key)
        if profile is None:
            raise MissingRule(f"atividade sem perfil confirmado: {act.description}")
        zeroed = a.zeroed(act.key)
        for tax in ("pis", "cofins"):
            if tax in zeroed:
                continue   # monofásico: alíquota zero na revenda
            if profile.cumulativo_no_real:
                cum_rev[tax] += act.receita
            else:
                nc_rev[tax] += act.receita
    exclusoes = a.decimal("pis_cofins_exclusoes", comp_scope(comp))
    creditos = a.decimal("pis_cofins_creditos_base", comp_scope(comp))
    lines = []
    for tax, nc_key, cum_key in (("pis", "pis_nao_cumulativo", "pis_cumulativo"), ("cofins", "cofins_nao_cumulativo", "cofins_cumulativo")):
        # exclusões (ex.: ICMS destacado) rateadas entre as receitas não cumulativas e cumulativas
        total_rev = nc_rev[tax] + cum_rev[tax]
        exc_nc = exclusoes * nc_rev[tax] / total_rev if total_rev else ZERO
        base_nc = max(ZERO, nc_rev[tax] - exc_nc)
        base_cum = max(ZERO, cum_rev[tax] - (exclusoes - exc_nc))
        nc_rate, cum_rate = D(rr[nc_key]), D(rr[cum_key])
        debito = base_nc * nc_rate
        anterior = saldo_credor.get(tax, ZERO)
        credito = creditos * nc_rate + anterior
        devido = max(ZERO, debito - credito)
        saldo_credor[tax] = max(ZERO, credito - debito)
        lines.append(Line("REAL", comp, tax, money(base_nc), nc_rate, money(devido),
                          f"receita não cumulativa {brl(base_nc)} × {pct(nc_rate, 2)} − créditos {brl(creditos)} × {pct(nc_rate, 2)}"
                          + (f" − saldo credor anterior {brl(anterior)}" if anterior else "")
                          + (f" [saldo credor {brl(saldo_credor[tax])} transportado]" if saldo_credor[tax] else ""),
                          rules.ref("real", nc_key), origin=a.origin("pis_cofins_creditos_base", comp_scope(comp)), verified=verified))
        if base_cum:
            lines.append(Line("REAL", comp, tax, money(base_cum), cum_rate, money(base_cum * cum_rate),
                              f"receita mantida no cumulativo {brl(base_cum)} × {pct(cum_rate, 2)}",
                              rules.ref("real", cum_key), verified=verified))
    return lines


def calculate(comps: list[str], view: SnapshotView, a: Assumptions, rules: RuleSet) -> list[Line]:
    lines: list[Line] = []
    saldo_pf = a.decimal("real.saldo_prejuizo_fiscal")
    saldo_bn = a.decimal("real.saldo_base_negativa_csll")
    icms_na_dre = a.boolean("real.icms_iss_ja_na_dre")
    saldo_credor: dict = {}
    for period, months in group_quarters(comps).items():
        lucro_antes = ZERO
        adicoes = exclusoes = ZERO
        for comp in months:
            lucro, o_lucro = _lucro_dre(view, comp)
            simples, o_simples = _despesa_simples(view, comp)
            if rules.consumo:   # 2027+: CBS/IBS no lugar do PIS/Cofins
                receita, exempt = _receita_mes(view, a, comp)
                icms_iss_mes = a.decimal("icms_regime_normal", comp_scope(comp)) + a.decimal("iss_regime_normal", comp_scope(comp))
                month_lines = cbs_ibs.month_lines("REAL", comp, receita, exempt, a, rules, saldo_credor, icms_iss_mes)
            else:
                month_lines = month_pis_cofins(comp, view, a, rules, saldo_credor)
            pis_cofins = sum((l.amount for l in month_lines), ZERO)
            payroll = charges("REAL", comp, view, a, rules)
            encargos = sum((l.amount for l in payroll), ZERO)
            icms_iss = ZERO
            for tax, key in (("icms", "icms_regime_normal"), ("iss", "iss_regime_normal")):
                value = a.decimal(key, comp_scope(comp))
                month_lines.append(Line("REAL", comp, tax, value, ZERO, money(value), f"{tax.upper()} no regime normal — premissa",
                                        rules.ref("premissa", key), origin=a.origin(key, comp_scope(comp)), verified=False))
                icms_iss += value
            descontar_icms = ZERO if icms_na_dre else icms_iss
            ajustado_mes = lucro + simples - encargos - pis_cofins - descontar_icms
            lines += month_lines + payroll
            lines.append(Line("REAL", comp, "reclassificacao_lucro", money(ajustado_mes), ZERO, money(ajustado_mes),
                              f"lucro da DRE {brl(lucro)} + despesa de Simples {brl(simples)} − encargos do regime {brl(encargos)}"
                              + (f" − CBS/IBS do regime {brl(pis_cofins)}" if rules.consumo
                                 else f" − PIS/Cofins do regime {brl(pis_cofins)}")
                              + ("" if icms_na_dre else f" − ICMS/ISS do regime {brl(icms_iss)}"),
                              rules.ref("real", "reclassificacao"), kind="reclassificacao",
                              origin={"lucro": o_lucro, "simples": o_simples}, verified=False))
            lucro_antes += ajustado_mes
            adicoes += a.decimal("real.adicoes", comp_scope(comp))
            exclusoes += a.decimal("real.exclusoes", comp_scope(comp))
        outcome = quarter_lines(QuarterProfit(
            period, len(months), lucro_antes, adicoes, exclusoes, saldo_pf, saldo_bn, partial=len(months) < 3,
            origin={"source": "calculo_trimestral", "period": period, "months": months,
                    "lucro": [_lucro_dre(view, c)[1] for c in months],
                    "premissas": [a.origin(k, s) for k, s in (("real.saldo_prejuizo_fiscal", "caso"),
                                                               ("real.saldo_base_negativa_csll", "caso"))]
                    + [a.origin(k, comp_scope(c)) for c in months for k in ("real.adicoes", "real.exclusoes")]},
        ), rules)
        lines += outcome.lines
        saldo_pf, saldo_bn = outcome.saldo_prejuizo, outcome.saldo_base_negativa
    return lines
