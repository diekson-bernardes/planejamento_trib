"""Orquestra elegibilidade e os três regimes; totaliza, ordena e calcula o hash do resultado."""
from dataclasses import dataclass, field
from decimal import Decimal

from worker.engine import presumido, real, simples
from worker.engine.assumptions import Assumptions
from worker.engine.eligibility import evaluate
from worker.engine.memory import REGIMES, ZERO, Line, canonical_hash, line_dict, money
from worker.engine.rules import MissingRule, RuleSet
from worker.engine.snapshot import SnapshotView

CALCULADO = "calculado"
NAO_CALCULADO = "nao_calculado"


class NoCompleteCompetence(Exception):
    code = "NO_COMPLETE_COMPETENCE"


@dataclass
class RegimeResult:
    regime: str
    status: str = CALCULADO
    total: Decimal = ZERO
    by_tax: dict = field(default_factory=dict)
    by_period: dict = field(default_factory=dict)
    pending: list = field(default_factory=list)
    partial_periods: list = field(default_factory=list)
    unverified_rules: int = 0

    def as_dict(self) -> dict:
        return {
            "regime": self.regime, "status": self.status, "total": str(self.total),
            "by_tax": {k: str(v) for k, v in sorted(self.by_tax.items())},
            "by_period": {k: str(v) for k, v in sorted(self.by_period.items())},
            "pending": self.pending, "partial_periods": self.partial_periods,
            "unverified_rules": self.unverified_rules,
        }


@dataclass
class SimulationResult:
    competences: list
    excluded: list
    eligibility: dict
    regimes: dict
    ranking: list
    alerts: list
    lines: list
    rules_version: str
    result_hash: str = ""

    def summary(self) -> dict:
        return {
            "competences": self.competences,
            "excluded_competences": self.excluded,
            "eligibility": {k: v.as_dict() for k, v in self.eligibility.items()},
            "regimes": {k: v.as_dict() for k, v in self.regimes.items()},
            "ranking": self.ranking,
            "alerts": self.alerts,
            "rules_version": self.rules_version,
        }


ENGINES = {
    "SIMPLES": lambda comps, view, a, rules: _simples(comps, view, a, rules),
    "PRESUMIDO": presumido.calculate,
    "REAL": real.calculate,
}


def _simples(comps, view, a, rules):
    lines, alerts = [], []
    for comp in comps:
        month_lines, month_alerts = simples.calculate_month(comp, view, a, rules)
        lines += month_lines
        alerts += month_alerts
    return lines, alerts


def calculate(view: SnapshotView, a: Assumptions, rules: RuleSet) -> SimulationResult:
    comps = view.complete_competences()
    if not comps:
        raise NoCompleteCompetence("nenhuma competência com PGDAS-D, folha, DRE e balancete homologados")
    eligibility = evaluate(view, comps, a, rules)
    out_of_force = [c for c in comps if not rules.in_force(c)]

    all_lines: list[Line] = []
    regimes: dict = {}
    alerts: list = []
    for regime in REGIMES:
        rr = RegimeResult(regime)
        regimes[regime] = rr
        if out_of_force:
            rr.status = NAO_CALCULADO
            rr.pending.append(f"sem regras vigentes para {', '.join(out_of_force)} (regras {rules.version}: exercício {rules.exercise})")
            continue
        try:
            produced = ENGINES[regime](comps, view, a, rules)
        except MissingRule as exc:
            rr.status = NAO_CALCULADO
            rr.pending.append(str(exc))
            continue
        if isinstance(produced, tuple):
            produced, regime_alerts = produced
            alerts += regime_alerts
        for line in produced:
            if line.kind != "tributo":
                continue
            rr.total += line.amount
            rr.by_tax[line.tax] = rr.by_tax.get(line.tax, ZERO) + line.amount
            rr.by_period[line.period] = rr.by_period.get(line.period, ZERO) + line.amount
            if line.partial and line.period not in rr.partial_periods:
                rr.partial_periods.append(line.period)
            if not line.verified:
                rr.unverified_rules += 1
        rr.total = money(rr.total)
        all_lines += produced

    ranking = sorted(
        (r for r in REGIMES if regimes[r].status == CALCULADO and eligibility[r].rankable),
        key=lambda r: (regimes[r].total, REGIMES.index(r)),
    )
    result = SimulationResult(
        competences=comps, excluded=view.excluded_competences(), eligibility=eligibility, regimes=regimes,
        ranking=ranking, alerts=alerts, lines=all_lines, rules_version=rules.version,
    )
    result.result_hash = canonical_hash({"summary": result.summary(), "lines": [line_dict(l) for l in all_lines]})
    return result
