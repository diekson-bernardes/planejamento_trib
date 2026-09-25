"""Elegibilidade dos três regimes: elegível, elegível com alerta, inelegível ou indeterminado."""
from dataclasses import dataclass, field
from decimal import Decimal

from worker.engine.assumptions import CASE, Assumptions
from worker.engine.memory import D, ZERO, brl
from worker.engine.rules import RuleSet
from worker.engine.snapshot import SnapshotView

ELEGIVEL = "elegivel"
ALERTA = "elegivel_com_alerta"
INELEGIVEL = "inelegivel"
INDETERMINADO = "indeterminado"
ORDER = [ELEGIVEL, ALERTA, INDETERMINADO, INELEGIVEL]


@dataclass
class EligibilityResult:
    regime: str
    status: str = ELEGIVEL
    reasons: list = field(default_factory=list)   # [{"status", "motivo", "regra", "origem"}]

    def add(self, status: str, motivo: str, regra: str, origem: dict | None = None) -> None:
        self.reasons.append({"status": status, "motivo": motivo, "regra": regra, "origem": origem or {}})
        if ORDER.index(status) > ORDER.index(self.status):
            self.status = status

    def as_dict(self) -> dict:
        return {"regime": self.regime, "status": self.status, "reasons": self.reasons}

    @property
    def rankable(self) -> bool:
        return self.status in (ELEGIVEL, ALERTA)


@dataclass(frozen=True)
class SublimitStatus:
    in_effect: bool
    rba_ytd: Decimal
    rbaa: Decimal


def year_to_date_revenue(view: SnapshotView, comp: str) -> Decimal:
    """RBA (acumulado antes do PA) + RPA da competência = receita do ano até a competência."""
    rba = view.value("PGDAS_D", comp, "receita.rba", "total") or ZERO
    rpa = view.value("PGDAS_D", comp, "receita.rpa", "total") or ZERO
    return rba + rpa


def sublimit_status(view: SnapshotView, comp: str, rules: RuleSet) -> SublimitStatus:
    """Sublimite produz efeito se a receita do ano anterior passou de R$ 3,6 mi ou a do ano passou de 20% acima."""
    lim = D(rules.elegibilidade["simples"]["sublimite_anual"])
    tol = D(rules.elegibilidade["simples"]["tolerancia_excesso"])
    rbaa = view.value("PGDAS_D", comp, "receita.rbaa", "total") or ZERO
    # RBA sem a RPA do mês de propósito: excesso acima de 20% produz efeito no mês SEGUINTE ao do excesso
    # (kb/simples-nacional/concepts/limites-sublimites-e-exclusao.md); no mês do excesso ICMS/ISS seguem no DAS.
    rba = view.value("PGDAS_D", comp, "receita.rba", "total") or ZERO
    return SublimitStatus(in_effect=rbaa > lim or rba > lim * (1 + tol), rba_ytd=rba, rbaa=rbaa)


def _declarations(result: EligibilityResult, decls: list, a: Assumptions, rules: RuleSet, regime: str) -> None:
    for d in decls:
        value = a.text(d["chave"]) or "nao_informado"
        ref = rules.ref("elegibilidade", regime, d["chave"])
        if value == d["impede_quando"]:
            result.add(INELEGIVEL, "Declarado: " + d["pergunta"], ref, a.origin(d["chave"]))
        elif value == "nao_informado":
            result.add(INDETERMINADO, "Não informado: " + d["pergunta"], ref, a.origin(d["chave"]))


def evaluate(view: SnapshotView, comps: list[str], a: Assumptions, rules: RuleSet) -> dict:
    latest = comps[-1]
    ytd = year_to_date_revenue(view, latest)
    elig = rules.elegibilidade

    # ------------------------------------------------------------------ Simples
    s = EligibilityResult("SIMPLES")
    teto = D(elig["simples"]["teto_anual"])
    tol = D(elig["simples"]["tolerancia_excesso"])
    rbaa = view.value("PGDAS_D", latest, "receita.rbaa", "total") or ZERO
    origin = view.origin(view.get("PGDAS_D", latest, "receita.rba", "total"))
    if ytd > teto * (1 + tol):
        s.add(INELEGIVEL, f"Receita do ano ({brl(ytd)}) acima do teto + 20% ({brl(teto * (1 + tol))}): exclusão no mês seguinte",
              rules.ref("elegibilidade", "simples", "teto_anual"), origin)
    elif ytd > teto:
        s.add(ALERTA, f"Receita do ano ({brl(ytd)}) acima do teto ({brl(teto)}): exclusão a partir do ano seguinte",
              rules.ref("elegibilidade", "simples", "teto_anual"), origin)
    if rbaa > teto:
        s.add(ALERTA, f"Receita do ano anterior ({brl(rbaa)}) acima do teto: confirmar a permanência no Simples",
              rules.ref("elegibilidade", "simples", "teto_anual"), origin)
    sub = sublimit_status(view, latest, rules)
    if sub.in_effect:
        s.add(ALERTA, "Sublimite estadual/municipal em efeito: ICMS/ISS recolhidos fora do DAS",
              rules.ref("elegibilidade", "simples", "sublimite_anual"), origin)
    _declarations(s, elig["simples"]["declaracoes"], a, rules, "simples")

    # ------------------------------------------------------------------ Presumido
    p = EligibilityResult("PRESUMIDO")
    limite = D(elig["presumido"]["limite_receita_ano_anterior"])
    anterior = a.raw("presumido.receita_total_ano_anterior", CASE)
    if anterior is None:
        p.add(INDETERMINADO, "Receita total do ano anterior não informada",
              rules.ref("elegibilidade", "presumido", "limite_receita_ano_anterior"),
              a.origin("presumido.receita_total_ano_anterior"))
    elif D(anterior) > limite:
        p.add(INELEGIVEL, f"Receita total do ano anterior ({brl(D(anterior))}) acima de {brl(limite)}: Lucro Real obrigatório",
              rules.ref("elegibilidade", "presumido", "limite_receita_ano_anterior"),
              a.origin("presumido.receita_total_ano_anterior"))
    if ytd > limite:
        p.add(ALERTA, f"Receita do ano ({brl(ytd)}) acima de {brl(limite)}: Presumido vedado no ano seguinte",
              rules.ref("elegibilidade", "presumido", "limite_receita_ano_anterior"), origin)
    _declarations(p, elig["presumido"]["declaracoes"], a, rules, "presumido")

    # ------------------------------------------------------------------ Real
    r = EligibilityResult("REAL")
    failing = [v for v in view.content.get("validations", []) if v.get("status") == "fail"]
    if failing:
        r.add(ALERTA, f"{len(failing)} validação(ões) interna(s) com falha no dossiê: confiança menor no lucro contábil",
              rules.ref("elegibilidade", "real", "qualidade_contabil"))
    return {"SIMPLES": s, "PRESUMIDO": p, "REAL": r}
