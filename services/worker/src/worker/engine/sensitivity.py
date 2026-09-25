"""Sensibilidade: ponto de virada por variável (grade + bisseção sobre o motor completo) e limite jurídico.

Para cada variável, a projeção é refeita com a alavanca correspondente e o motor recalcula os três regimes.
- Ponto de virada: valor em que o primeiro colocado entre os regimes elegíveis muda.
- Limite jurídico: valor em que o conjunto de regimes elegíveis muda (reportado à parte, não como virada).
A distância é medida a partir do cenário base; a robustez segue as faixas de `decisao.json`.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from worker.engine.assumptions import Assumptions
from worker.engine.calculate import calculate
from worker.engine.decision_params import DecisionParams, Variable
from worker.engine.memory import ZERO, D
from worker.engine.projection import Levers, ProjectedCase, ProjectionError, build_projection
from worker.engine.rules import RuleSet
from worker.engine.snapshot import SnapshotView

BASE_FIELD = {"receita": "receita_anual", "margem": "margem_anual", "folha": "folha_anual"}


@dataclass
class Point:
    x: Decimal
    ranking: tuple            # regimes elegíveis e calculados, do mais barato ao mais caro
    totals: dict

    @property
    def leader(self) -> str | None:
        return self.ranking[0] if self.ranking else None

    @property
    def eligible(self) -> tuple:
        return tuple(sorted(self.ranking))


@dataclass
class SensitivityResult:
    key: str
    label: str
    kind: str
    base_x: Decimal                 # posição do cenário base no eixo (1 para multiplicador; margem base para absoluto)
    base_value: Decimal | None      # valor em unidade natural (R$ ou fração)
    leader: str | None
    turning_x: Decimal | None = None
    turning_value: Decimal | None = None
    new_leader: str | None = None
    distance: Decimal | None = None
    robustness: str | None = None
    legal_x: Decimal | None = None
    legal_value: Decimal | None = None
    legal_change: dict = field(default_factory=dict)
    runs: int = 0

    def as_dict(self) -> dict:
        def s(v, places="0.000001"):
            return None if v is None else str(v.quantize(Decimal(places)))
        return {
            "variavel": self.key, "rotulo": self.label, "tipo": self.kind,
            "base_x": s(self.base_x), "base_valor": s(self.base_value, "0.01") if self.kind == "multiplicador" else s(self.base_value),
            "lider_base": self.leader,
            "virada_x": s(self.turning_x),
            "virada_valor": (s(self.turning_value, "0.01") if self.kind == "multiplicador" else s(self.turning_value)),
            "novo_lider": self.new_leader, "distancia": s(self.distance, "0.0001"), "robustez": self.robustness,
            "limite_juridico_x": s(self.legal_x),
            "limite_juridico_valor": (s(self.legal_value, "0.01") if self.kind == "multiplicador" else s(self.legal_value)),
            "limite_juridico": self.legal_change or None,
            "sem_virada": self.turning_x is None,
            "execucoes": self.runs,
        }


def _levers(var: Variable, x: Decimal) -> Levers:
    if var.key == "margem":
        return Levers(margem=x)
    return Levers(**{var.key: x})


def _base_value(var: Variable, base: ProjectedCase) -> Decimal | None:
    if var.key in BASE_FIELD:
        return D(base.base[BASE_FIELD[var.key]])
    taxes = {"creditos": None, "icms_iss": ("icms_regime_normal", "iss_regime_normal")}[var.key]
    keys = ("pis_cofins_creditos_base",) if taxes is None else taxes
    return sum((D(r["value"]) for r in base.assumptions if r["key"] in keys), ZERO)


def run_sensitivity(view: SnapshotView, confirmed: Assumptions, rules: RuleSet, params: DecisionParams,
                    base: ProjectedCase, base_ranking: list) -> list[SensitivityResult]:
    out = []
    for var in params.variables:
        out.append(_one(var, view, confirmed, rules, params, base, base_ranking))
    return out


def _one(var: Variable, view, confirmed, rules, params, base: ProjectedCase, base_ranking: list) -> SensitivityResult:
    cache: dict = {}

    def at(x: Decimal) -> Point | None:
        x = x.quantize(Decimal("0.000001"))
        if x not in cache:
            try:
                pc = build_projection(view, confirmed, params, _levers(var, x))
                sim = calculate(SnapshotView(pc.content), Assumptions(pc.assumptions), rules)
                cache[x] = Point(x, tuple(sim.ranking), {r: v.total for r, v in sim.regimes.items()})
            except ProjectionError:
                cache[x] = None
        return cache[x]

    base_x = D(base.base["margem_anual"]) if var.kind == "absoluto" else Decimal("1")
    result = SensitivityResult(var.key, var.label, var.kind, base_x, _base_value(var, base),
                               base_ranking[0] if base_ranking else None)
    if not base_ranking:
        return result
    # o ponto base é calculado pelo mesmo caminho dos demais pontos do eixo (ex.: margem aplicada a todos os meses),
    # para que uma troca de líder entre ele e o vizinho seja efeito da variável, não do método
    base_point = at(base_x) or Point(base_x, tuple(base_ranking), {})
    base_eligible = tuple(sorted(base_ranking))
    n = params.grid_points
    step = (var.high - var.low) / (n - 1)
    grid = sorted({var.low + step * i for i in range(n)} | {base_x})
    points = [base_point if x == base_x else at(x) for x in grid]
    pairs = [(a, b) for a, b in zip(points, points[1:]) if a is not None and b is not None]
    tolerance = (var.high - var.low) * params.precision

    def bisect(a: Point, b: Point, changed) -> tuple[Decimal, Point]:
        """Estreita [a, b] até a precisão; devolve a fronteira e o ponto do lado oposto ao cenário base."""
        far = a if abs(a.x - base_x) > abs(b.x - base_x) else b
        for _ in range(params.bisection_steps):
            if abs(b.x - a.x) <= tolerance:
                break
            mid = at((a.x + b.x) / 2)
            if mid is None:
                break
            if changed(a, mid):
                b = mid
            else:
                a = mid
        return (a.x + b.x) / 2, far

    def nearest(candidates):
        return min(candidates, key=lambda c: abs(c[0] - base_x), default=None)

    legal = [bisect(a, b, lambda p, q: p.eligible != q.eligible) for a, b in pairs if a.eligible != b.eligible]
    # virada só na região com os mesmos regimes elegíveis do cenário base (além de um limite jurídico, a troca de
    # posição entre os que sobram não é virada da recomendação)
    turning = [bisect(a, b, lambda p, q: p.leader != q.leader) for a, b in pairs
               if a.eligible == b.eligible == base_eligible and a.leader != b.leader]
    t = nearest(turning)
    if t is not None:
        result.turning_x, far = t
        result.new_leader = far.leader
        result.distance = abs(result.turning_x - base_x) / abs(base_x) if base_x else abs(result.turning_x)
        result.robustness = params.robustness(result.distance)
    l = nearest(legal)
    if l is not None:
        result.legal_x, far = l
        result.legal_change = {"elegiveis_alem_do_limite": list(far.eligible), "elegiveis_base": list(base_point.eligible)}
    scale = result.base_value if var.kind == "multiplicador" else None
    if result.turning_x is not None:
        result.turning_value = result.turning_x * scale if scale is not None else result.turning_x
    if result.legal_x is not None:
        result.legal_value = result.legal_x * scale if scale is not None else result.legal_x
    result.runs = len(cache)
    return result
