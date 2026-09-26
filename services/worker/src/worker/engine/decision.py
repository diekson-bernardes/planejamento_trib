"""Orquestra a decisão do exercício: projeção → motor → sensibilidade → recomendação, com hash do resultado."""
import time
from dataclasses import dataclass, replace
from decimal import Decimal

from worker.engine.assumptions import Assumptions
from worker.engine.calculate import SimulationResult, calculate
from worker.engine.decision_params import DecisionParams
from worker.engine.memory import canonical_hash, line_dict, pct
from worker.engine.projection import Levers, ProjectedCase, build_projection, shift_year
from worker.engine.recommendation import Recommendation, recommend
from worker.engine.rules import RuleSet
from worker.engine.sensitivity import SensitivityResult, run_sensitivity
from worker.engine.snapshot import SnapshotView

MONTH_NAME = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun", 7: "jul", 8: "ago", 9: "set",
              10: "out", 11: "nov", 12: "dez"}
DOMAIN_NOTE = {"presumido": "Lucro Presumido (inclui LC 224 trimestral)", "real": "Lucro Real",
               "encargos": "encargos da folha", "elegibilidade": "elegibilidade", "atividades": "perfis de atividade",
               "simples": "Simples Nacional"}


@dataclass
class ProjectionResult:
    projected: ProjectedCase
    simulation: SimulationResult
    sensitivity: list
    recommendation: Recommendation
    result_hash: str
    runs: int
    duration_ms: int

    def summary(self) -> dict:
        return {
            "year": self.projected.year,
            "origins": self.projected.origins,
            "base": self.projected.base,
            "simulation": self.simulation.summary(),
        }

    def lines(self) -> list[dict]:
        out = []
        for line in self.simulation.lines:
            d = line_dict(line)
            period = d["period"]
            origin = self.projected.origins.get(period)
            if origin is None and "-T" in period:   # IRPJ/CSLL trimestrais: origens dos três meses
                q = int(period[-1])
                months = {self.projected.origins.get(f"{period[:4]}-{m:02d}") for m in range(3 * q - 2, 3 * q + 1)}
                origin = months.pop() if len(months) == 1 else "+".join(sorted(months))
            d["origin"] = {**(d.get("origin") or {}), "mes_origem": origin}
            out.append(d)
        return out


def _months(origins: dict, kind: str) -> str:
    months = [int(m[5:7]) for m, o in sorted(origins.items()) if o == kind]
    return ", ".join(MONTH_NAME[m] for m in months)


def project(view: SnapshotView, confirmed: Assumptions, rules: RuleSet, params: DecisionParams,
            threshold: Decimal, blockers: list | None = None, base_params: DecisionParams | None = None) -> ProjectionResult:
    """Projeção do exercício de `rules`. Se o exercício é posterior ao dos meses completos (ex.: 2027), a projeção do
    ano base (com `base_params`) é deslocada com o crescimento confirmado (`reforma.crescimento`).

    Levanta ProjectionError quando não há dado mínimo para projetar (sem competência completa etc.)."""
    started = time.monotonic()
    base_year = int(view.complete_competences()[-1][:4]) if view.complete_competences() else rules.exercise
    shifted = rules.exercise > base_year
    growth = confirmed.decimal("reforma.crescimento") if shifted else Decimal("0")
    base_params = base_params or params

    def builder(levers: Levers = Levers()) -> ProjectedCase:
        if not shifted:
            return build_projection(view, confirmed, params, levers)
        pc = build_projection(view, confirmed, base_params, replace(levers, cbs=Decimal("1")))
        return shift_year(pc, params, growth, levers)

    base = builder()
    sim = calculate(SnapshotView(base.content), Assumptions(base.assumptions), rules)
    sens: list[SensitivityResult] = run_sensitivity(view, confirmed, rules, params, base, sim.ranking, builder)
    unverified = [DOMAIN_NOTE.get(d, d) for d, ok in sorted(rules.verified.items()) if not ok]
    caveats = []
    if unverified:
        caveats.append("Regras ainda não conferidas na fonte primária (" + rules.version + "): " + ", ".join(unverified) + ".")
    if shifted:
        taxas = ", ".join(f"{t.upper()} {pct(confirmed.decimal(k), 2)}" for t, k in
                          (("cbs", "reforma.cbs_aliquota"), ("ibs", "reforma.ibs_aliquota")) if confirmed.raw(k) is not None)
        caveats.append(f"Exercício {base.year} projetado a partir de {base_year} com crescimento de {pct(growth, 2)}"
                       + (f"; alíquotas informadas: {taxas}." if taxas else "; alíquotas de CBS/IBS não informadas."))
    for kind, label in (("estimado", "Meses estimados"), ("projetado", "Meses projetados pela média"),
                        ("orcamento", "Meses com orçamento informado")):
        months = _months(base.origins, kind)
        if months and not shifted:
            caveats.append(f"{label}: {months}/{base.year}.")
    blockers = list(blockers or [])
    if rules.consumo:   # sem alíquota, os regimes regulares ficam "não calculados": não recomendar só entre os demais
        missing = [t["premissa_aliquota"] for t in rules.consumo["tributos"].values()
                   if confirmed.raw(t["premissa_aliquota"]) is None]
        if missing:
            blockers.append(f"alíquotas de {rules.exercise} não informadas ({', '.join(missing)}) — "
                            "gere/regenere as premissas e informe as alíquotas")
    rec = recommend(sim, sens, confirmed, params, threshold, Decimal(base.base["receita_anual"]),
                    "SIMPLES" if view.competences_with("PGDAS_D") else None, blockers, caveats)
    runs = 1 + sum(s.runs for s in sens)
    payload = {
        "summary": sim.summary(), "lines": [line_dict(l) for l in sim.lines], "origins": base.origins,
        "base": base.base, "sensitivity": [s.as_dict() for s in sens], "recommendation": rec.as_dict(),
        "decision": params.hash, "threshold": str(threshold),
    }
    return ProjectionResult(base, sim, sens, rec, canonical_hash(payload), runs,
                            int((time.monotonic() - started) * 1000))
