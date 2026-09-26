"""Simples Nacional: DAS mensal por atividade, com memória de cálculo."""
from dataclasses import dataclass
from decimal import Decimal

from worker.engine import cbs_ibs
from worker.engine.assumptions import Assumptions, comp_scope
from worker.engine.eligibility import sublimit_status
from worker.engine.memory import HIBRIDO, D, ZERO, Line, brl, money, pct
from worker.engine.payroll import charges
from worker.engine.rules import Band, MissingRule, RuleSet
from worker.engine.snapshot import SnapshotView, previous_months

LOCAL_TAXES = ("icms", "iss")


@dataclass(frozen=True)
class Rbt12:
    value: Decimal
    declared: Decimal | None
    source: str       # "serie" | "declarado"


def effective_rate(rbt12: Decimal, band: Band) -> Decimal:
    if rbt12 <= 0:
        return band.nominal
    return (rbt12 * band.nominal - band.deduzir) / rbt12


def compute_rbt12(view: SnapshotView, comp: str) -> Rbt12:
    series = view.pgdas_series(comp, "receita_anterior")
    months = previous_months(comp, 12)
    declared = view.value("PGDAS_D", comp, "receita.rbt12", "total")
    if all(m in series for m in months):
        return Rbt12(sum((series[m] for m in months), ZERO), declared, "serie")
    if declared is not None:
        return Rbt12(declared, declared, "declarado")
    raise MissingRule("RBT12 indisponível: série de receitas anteriores incompleta e sem valor declarado")


def band_rates(anexo_code: str, rbt12: Decimal, rules: RuleSet, zeroed: set, sublimite_em_efeito: bool) -> list:
    """(tributo, alíquota, regra, fórmula) por tributo do anexo — aplica teto de ISS e faixa 5 para ICMS/ISS."""
    anexo = rules.anexos.get(anexo_code)
    if anexo is None:
        raise MissingRule(f"anexo {anexo_code} sem regra")
    band = anexo.band_for(rbt12)
    if band is None:
        raise MissingRule(f"RBT12 {brl(rbt12)} acima da última faixa do anexo {anexo_code}")
    efetiva = effective_rate(rbt12, band)
    teto_iss = D(rules.simples["iss_teto_efetivo"])
    out = []

    iss_cap_mode = None
    if "iss" in anexo.taxes and band.iss_excess and efetiva > band.iss_excess["limiar"]:
        iss_cap_mode = "tabela"      # nota (*) dos Anexos III e IV: ISS fixo em 5%, excedente redistribuído
    elif "iss" in anexo.taxes and efetiva * band.share("iss") > teto_iss:
        iss_cap_mode = "proporcional"

    federal = [t for t in anexo.taxes if t not in LOCAL_TAXES]
    federal_share_total = sum((band.share(t) for t in federal), ZERO)

    for tax in anexo.taxes:
        base_ref = rules.ref("simples", "anexo_" + anexo_code, "faixa_" + str(band.faixa), tax)
        if tax in zeroed:
            continue
        if tax in LOCAL_TAXES and sublimite_em_efeito:
            continue   # fora do DAS: calculado pelo regime normal (premissa)
        if tax in LOCAL_TAXES and band.faixa == 6 and not sublimite_em_efeito:
            b5 = anexo.band_number(5)
            ef5 = effective_rate(rbt12, b5)
            rate = ef5 * b5.share(tax)
            if tax == "iss" and rate > teto_iss:
                rate = teto_iss
            out.append((tax, rate, rules.ref("simples", "faixa6_icms_iss_pela_faixa5", "anexo_" + anexo_code, tax),
                        f"efetiva da 5ª faixa {pct(ef5)} × repartição {pct(b5.share(tax), 2)}", False))
            continue
        if iss_cap_mode == "tabela":
            if tax == "iss":
                rate = teto_iss
                formula = "ISS fixo em 5% (efetiva acima do limiar da 5ª faixa)"
            else:
                rate = (efetiva - teto_iss) * band.iss_excess["shares"][tax]
                formula = f"(efetiva {pct(efetiva)} − 5%) × {pct(band.iss_excess['shares'][tax], 2)}"
        elif iss_cap_mode == "proporcional":
            iss_original = efetiva * band.share("iss")
            if tax == "iss":
                rate = teto_iss
                formula = "ISS limitado a 5% efetivos"
            else:
                extra = (iss_original - teto_iss) * band.share(tax) / federal_share_total if tax in federal else ZERO
                rate = efetiva * band.share(tax) + extra
                formula = f"efetiva {pct(efetiva)} × {pct(band.share(tax), 2)} + excedente de ISS proporcional"
        else:
            rate = efetiva * band.share(tax)
            formula = f"efetiva {pct(efetiva)} × repartição {pct(band.share(tax), 2)}"
        out.append((tax, rate, base_ref, formula, True))
    return out, band, efetiva


def calculate_month(comp: str, view: SnapshotView, a: Assumptions, rules: RuleSet, hybrid: bool = False,
                    saldo: dict | None = None) -> tuple[list[Line], list[str]]:
    """Linhas do DAS da competência + encargos fora do DAS (Anexo IV). Levanta MissingRule se faltar regra.

    `hybrid` (2027+): CBS/IBS saem do DAS e são apurados no regime regular (débito − crédito), com `saldo` credor."""
    regime = HIBRIDO if hybrid else "SIMPLES"
    alerts = []
    rbt = compute_rbt12(view, comp)
    if rbt.declared is not None and money(rbt.declared) != money(rbt.value):
        alerts.append(f"{comp}: RBT12 recalculado ({brl(rbt.value)}) difere do declarado ({brl(rbt.declared)}); usado o recalculado")
    sub = sublimit_status(view, comp, rules)
    activities = view.activities(comp)
    if not activities:
        raise MissingRule(f"{comp}: PGDAS-D sem atividades")
    lines: list[Line] = []
    rbt_origin = {"source": "snapshot", "field_key": "receita_anterior.*", "competence": comp, "rbt12_source": rbt.source}
    lines.append(Line(regime, comp, "rbt12", money(rbt.value), ZERO, money(rbt.value),
                      "soma das receitas dos 12 meses anteriores (série 2.2 do PGDAS-D)" if rbt.source == "serie"
                      else "RBT12 declarado no PGDAS-D", rules.ref("simples", "rbt12"), kind="informativo", origin=rbt_origin))
    total_receita = sum((act.receita for act in activities), ZERO)
    anexo_iv_receita = ZERO
    exempt = ZERO
    for act in activities:
        profile = a.profile(act.key)
        if profile is None:
            raise MissingRule(f"atividade sem perfil confirmado: {act.description}")
        anexo = profile.anexo
        if profile.fator_r:
            if a.raw("folha.folha_12m", comp_scope(comp)) is None:
                # sem a folha o Fator R cairia silenciosamente no Anexo V
                raise MissingRule(f"{comp}: folha dos 12 meses (Fator R) não confirmada — regenere as premissas")
            folha = a.decimal("folha.folha_12m", comp_scope(comp))
            r = folha / rbt.value if rbt.value else ZERO
            anexo = "III" if r >= D(rules.simples["fator_r_minimo"]) else "V"
            lines.append(Line(regime, comp, "fator_r", money(folha), r, ZERO,
                              f"folha 12m {brl(folha)} ÷ RBT12 {brl(rbt.value)} = {pct(r, 2)} → Anexo {anexo}",
                              rules.ref("simples", "fator_r_minimo"), kind="informativo", activity=act.key,
                              origin=a.origin("folha.folha_12m", comp_scope(comp))))
        if anexo == "IV":
            anexo_iv_receita += act.receita
        zeroed = set(a.zeroed(act.key))
        if rules.consumo:
            if zeroed & set(rules.simples.get("cbs_substitui", [])):
                zeroed.add("cbs")           # monofásico de PIS/Cofins → parcela de CBS zerada (hipótese)
                exempt += act.receita
            if hybrid:
                zeroed |= {"cbs", "ibs"}    # híbrido: CBS/IBS fora do DAS
        rates, band, efetiva = band_rates(anexo, rbt.value, rules, zeroed, sub.in_effect)
        for tax, rate, ref, formula, verified in rates:
            lines.append(Line(regime, comp, tax, act.receita, rate, money(act.receita * rate),
                              f"receita {brl(act.receita)} × ({formula})", ref, origin=act.origin,
                              activity=act.key, verified=verified and rules.verified.get("simples", False)))
    if sub.in_effect:
        for tax, key in (("icms", "icms_regime_normal"), ("iss", "iss_regime_normal")):
            value = a.decimal(key, comp_scope(comp))
            lines.append(Line(regime, comp, tax, value, ZERO, money(value),
                              f"{tax.upper()} fora do DAS (sublimite em efeito) — premissa", rules.ref("simples", "sublimite"),
                              origin=a.origin(key, comp_scope(comp)), verified=False))
    if anexo_iv_receita > 0 and total_receita > 0:
        share = anexo_iv_receita / total_receita
        lines.extend(charges(regime, comp, view, a, rules, share, " (Anexo IV: CPP fora do DAS)"))
    if hybrid:
        icms_iss = sum((l.amount for l in lines if l.tax in LOCAL_TAXES and l.kind == "tributo"), ZERO)   # DAS e fora dele
        lines += cbs_ibs.month_lines(regime, comp, total_receita, exempt, a, rules, saldo if saldo is not None else {},
                                     icms_iss)
    return lines, alerts
