"""Recomendação determinística a partir da projeção e da sensibilidade (PRD §10.2–10.3).

Estados: recomendado (diferença entre os dois primeiros elegíveis ≥ limiar), inconclusivo (< limiar) e
bloqueado (dado crítico ausente). O custo de conformidade é exibido por regime e nunca altera a ordem.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from worker.engine.assumptions import Assumptions
from worker.engine.decision_params import DecisionParams
from worker.engine.memory import REGIMES, ZERO, brl as _brl, money, pct

def brl(value: Decimal) -> str:
    return "R$ " + _brl(value)


RECOMENDADO, INCONCLUSIVO, BLOQUEADO = "recomendado", "inconclusivo", "bloqueado"
REGIME_NAME = {"SIMPLES": "Simples Nacional", "PRESUMIDO": "Lucro Presumido", "REAL": "Lucro Real",
               "SIMPLES_HIBRIDO": "Simples Nacional (híbrido: CBS/IBS no regime regular)"}
TAX_NAME = {"cbs": "CBS", "ibs": "IBS", "irpj": "IRPJ", "adicional_irpj": "adicional de IRPJ", "csll": "CSLL", "pis": "PIS", "cofins": "Cofins",
            "icms": "ICMS", "iss": "ISS", "ipi": "IPI", "cpp": "CPP", "rat": "RAT", "terceiros": "terceiros"}


@dataclass
class Recommendation:
    status: str
    regime: str | None = None
    second: str | None = None
    text: str = ""
    factors: list = field(default_factory=list)
    savings_vs_second: Decimal | None = None
    savings_vs_second_pct: Decimal | None = None
    current_regime: str | None = None
    savings_vs_current: Decimal | None = None
    loads: dict = field(default_factory=dict)
    effective_rates: dict = field(default_factory=dict)
    compliance: dict = field(default_factory=dict)
    excluded: list = field(default_factory=list)
    blockers: list = field(default_factory=list)
    caveats: list = field(default_factory=list)
    threshold: Decimal = ZERO

    def as_dict(self) -> dict:
        def s(v):
            return None if v is None else str(v)
        return {
            "status": self.status, "regime": self.regime, "segundo": self.second, "texto": self.text,
            "fatores": self.factors, "economia_vs_segundo": s(self.savings_vs_second),
            "economia_vs_segundo_pct": s(self.savings_vs_second_pct), "regime_atual": self.current_regime,
            "economia_vs_atual": s(self.savings_vs_current),
            "carga": {r: {k: str(v) for k, v in g.items()} for r, g in self.loads.items()},
            "aliquota_efetiva": {r: str(v) for r, v in self.effective_rates.items()},
            "conformidade": {r: str(v) for r, v in self.compliance.items()},
            "excluidos": self.excluded, "bloqueios": self.blockers, "ressalvas": self.caveats,
            "limiar": str(self.threshold),
        }


def compliance_costs(a: Assumptions, regimes=REGIMES) -> dict:
    return {r: a.decimal("conformidade.custo_anual", "regime:" + r) for r in regimes
            if a.raw("conformidade.custo_anual", "regime:" + r) is not None}


def recommend(sim, sensitivity: list, a: Assumptions, params: DecisionParams, threshold: Decimal,
              annual_revenue: Decimal, current_regime: str | None, blockers: list,
              extra_caveats: list | None = None) -> Recommendation:
    rec = Recommendation(status=BLOQUEADO, threshold=threshold, current_regime=current_regime,
                         compliance=compliance_costs(a, tuple(sim.regimes)), blockers=list(blockers))
    rec.caveats = list(params.caveats) + list(extra_caveats or [])
    for regime, rr in sim.regimes.items():
        if rr.status != "calculado":
            rec.excluded.append({"regime": regime, "motivo": "não calculado", "detalhe": rr.pending})
        elif not sim.eligibility[regime].rankable:
            rec.excluded.append({"regime": regime, "motivo": "inelegível", "detalhe": [
                r["motivo"] + " (" + r["regra"] + ")" for r in sim.eligibility[regime].as_dict()["reasons"]]})
        rec.loads[regime] = {g: money(sum((rr.by_tax.get(t, ZERO) for t in taxes), ZERO))
                             for g, taxes in params.load_groups.items()}
        if annual_revenue:
            rec.effective_rates[regime] = (rr.total / annual_revenue).quantize(Decimal("0.0001"))
    ranking = list(sim.ranking)
    if not ranking:
        rec.blockers.append("nenhum regime elegível e calculado")
    if rec.blockers:
        rec.text = "Recomendação bloqueada: " + "; ".join(rec.blockers) + ". Prévia incompleta."
        return rec

    win = ranking[0]
    total = {r: sim.regimes[r].total for r in ranking}
    rec.regime = win
    if current_regime in total:
        rec.savings_vs_current = money(total[current_regime] - total[win])
    if len(ranking) == 1:
        rec.status = RECOMENDADO
        rec.text = (f"Recomendamos o {REGIME_NAME[win]} porque é o único regime elegível e calculado "
                    f"(custo tributário de {brl(total[win])} no exercício).")
        return rec
    second = ranking[1]
    rec.second = second
    diff = total[second] - total[win]
    rec.savings_vs_second = money(diff)
    rec.savings_vs_second_pct = (diff / total[win]).quantize(Decimal("0.0001")) if total[win] else None
    by_win, by_second = sim.regimes[win].by_tax, sim.regimes[second].by_tax
    deltas = sorted(((by_second.get(t, ZERO) - by_win.get(t, ZERO), t) for t in set(by_win) | set(by_second)),
                    key=lambda d: (-d[0], d[1]))
    for delta, tax in deltas[:3]:
        if delta <= 0:
            break
        rec.factors.append({
            "tributo": tax, "diferenca": str(money(delta)),
            "texto": f"{TAX_NAME.get(tax, tax)}: {brl(by_win.get(tax, ZERO))} no {REGIME_NAME[win]} "
                     f"contra {brl(by_second.get(tax, ZERO))} no {REGIME_NAME[second]}",
        })
    fragile = [s for s in sensitivity if s.robustness in ("fragil", "atencao")]
    turning = "; ".join(f"{s.label}: virada a {pct(s.distance, 1)} do cenário base ({s.new_leader})" for s in fragile)
    if rec.savings_vs_second_pct is not None and rec.savings_vs_second_pct >= threshold:
        rec.status = RECOMENDADO
        rec.text = (f"Recomendamos o {REGIME_NAME[win]} porque o custo tributário projetado do exercício "
                    f"({brl(total[win])}) é {brl(diff)} ({pct(rec.savings_vs_second_pct, 2)}) menor que o do "
                    f"{REGIME_NAME[second]}, segundo colocado.")
    else:
        rec.status = INCONCLUSIVO
        rec.text = (f"Resultado inconclusivo: o {REGIME_NAME[win]} ({brl(total[win])}) fica {brl(diff)} "
                    f"({pct(rec.savings_vs_second_pct or ZERO, 2)}) abaixo do {REGIME_NAME[second]}, diferença menor "
                    f"que o limiar de {pct(threshold, 2)} do escritório. Priorizar a análise de sensibilidade.")
    if turning:
        rec.text += " Atenção: " + turning + "."
    return rec
