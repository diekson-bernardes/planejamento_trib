"""Fator R do planejamento rápido (ciclo 6): folha dos 12 meses anteriores mês a mês e simulação da "folha ideal".

- Folha do mês = salários × (1 + FGTS) + pró-labore (LC 123 art. 18 § 24; a CPP do Anexo III/V já está no DAS).
- Meses com folha informada (PDF ou digitação) usam o valor informado; meses depois da declaração de faturamento usam
  a folha projetada; meses da declaração sem folha são "sem folha" e seguem a escolha `rapido.folha_incompleta`
  (completar pela média dos meses informados ou considerar zero). Sem escolha, o cálculo para.
- A folha 12m é derivada (não é premissa editável no rápido) e entra nas premissas `folha.folha_12m` de cada mês do
  exercício projetado, inclusive nos cenários da sensibilidade (a alavanca de folha já está na folha projetada).
- Folha ideal: linhas informativas (fora dos totais) com a folha mensal que falta para 28% e o custo de completá-la
  por pró-labore ou por salário, ao lado da economia de Simples do Anexo III em relação ao V.

Parâmetros em `rules/fator_r.json`, com versão e hash próprios (não entram no hash das regras do exercício)."""
import hashlib
import json
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Callable

from worker.engine.assumptions import comp_scope
from worker.engine.memory import D, ZERO, Line, brl, money, pct
from worker.engine.rules import RuleSet, RulesError
from worker.engine.snapshot import SnapshotView, previous_months

FOLHA_KEY = "folha.folha_12m"
TRATAMENTO_KEY = "rapido.folha_incompleta"
TRATAMENTOS = ("media", "zero")
MSG_ESCOLHA = "Fator R: escolha como tratar os meses sem folha"


class FolhaIncompletaError(Exception):
    """Atividade com Fator R, meses sem folha na janela de 12 meses e nenhuma escolha registrada."""

    code = "FOLHA_INCOMPLETA"


@dataclass(frozen=True)
class FatorRParams:
    version: str
    hash: str
    verified: bool
    fgts: Decimal
    inss_socio: Decimal
    provisoes_salario: Decimal


def load_fator_r_params(path: str | Path) -> FatorRParams:
    path = Path(path)
    if not path.is_file():
        raise RulesError(f"parâmetros do Fator R ausentes: {path}")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    try:
        doc = json.loads(raw)
        params = FatorRParams(doc["versao"], hashlib.sha256(raw).hexdigest(), bool(doc.get("verificado", False)),
                              D(doc["fgts"]), D(doc["inss_socio"]), D(doc["provisoes_salario"]))
    except (json.JSONDecodeError, KeyError, ArithmeticError) as exc:
        raise RulesError(f"parâmetros do Fator R inválidos em {path}: {exc}") from exc
    if not (ZERO <= params.fgts < 1 and ZERO <= params.inss_socio < 1 and ZERO <= params.provisoes_salario < 1):
        raise RulesError("parâmetros do Fator R fora de 0–1")
    return params


def folha_mes(empregados: Decimal, socios: Decimal, params: FatorRParams) -> Decimal:
    return empregados * (1 + params.fgts) + socios


def build_timeline(informed: dict, realized: set, last_declared: str, history: dict, params: FatorRParams) -> dict:
    """Mês → folha do Fator R ou None (mês da declaração sem folha).

    `informed`: mês → (salários, pró-labore) informados; `history`: mês → (salários, pró-labore) da projeção, já com a
    alavanca de folha (meses realizados e projetados)."""
    out: dict = {}
    for m in sorted(set(informed) | set(history)):
        if m in realized and m in history:
            out[m] = folha_mes(*history[m], params)
        elif m in informed:
            out[m] = folha_mes(*informed[m], params)
        elif m > last_declared:
            out[m] = folha_mes(*history[m], params)
        else:
            out[m] = None
    return out


def missing_months(comps: list[str], informed: dict, last_declared: str) -> list[str]:
    """Meses sem folha informada nas janelas de 12 meses das competências `comps` (até o último mês declarado)."""
    window = {m for c in comps for m in previous_months(c, 12)}
    return sorted(m for m in window if m <= last_declared and m not in informed)


def folha_12m(comp: str, timeline: dict, tratamento: str | None) -> tuple[Decimal, dict]:
    months = previous_months(comp, 12)
    known = [timeline[m] for m in months if timeline.get(m) is not None]
    missing = len(months) - len(known)
    if missing and tratamento not in TRATAMENTOS:
        raise FolhaIncompletaError(MSG_ESCOLHA)
    if missing and tratamento == "media" and not known:
        raise FolhaIncompletaError("Fator R: sem nenhum mês de folha, só é possível considerar zero")
    fill = sum(known, ZERO) / len(known) if missing and tratamento == "media" else ZERO
    total = money(sum(known, ZERO) + fill * missing)
    return total, {"meses_informados": len(known), "meses_sem_folha": missing,
                   "tratamento": tratamento if missing else None}


def make_adjuster(informed: dict, realized: set, last_declared: str, tratamento: str | None,
                  params: FatorRParams) -> Callable:
    """Função aplicada a cada ProjectedCase (base e sensibilidade): troca `folha.folha_12m` dos meses do exercício pela
    folha 12m derivada da linha do tempo."""
    def adjust(pc):
        timeline = build_timeline(informed, realized, last_declared, pc.payroll_history, params)
        months = sorted(pc.plan)
        rows = [r for r in pc.assumptions if not (r["key"] == FOLHA_KEY and r["scope"].removeprefix("competencia:") in months)]
        for m in months:
            value, _ = folha_12m(m, timeline, tratamento)
            rows.append({"key": FOLHA_KEY, "scope": comp_scope(m), "value": str(value)})
        return replace(pc, assumptions=rows)
    return adjust


def folha_ideal_lines(lines: list[Line], content: dict, rules: RuleSet, params: FatorRParams) -> list[Line]:
    """Linhas informativas por competência e atividade no Anexo V pelo Fator R (regime SIMPLES)."""
    from worker.engine.simples import band_rates, compute_rbt12

    minimo = D(rules.simples["fator_r_minimo"])
    view = SnapshotView(content)
    ref = f"fator_r.json {params.version} ({params.hash[:12]})"
    out: list[Line] = []
    for l in lines:
        if l.tax != "fator_r" or l.regime != "SIMPLES" or l.rate >= minimo:
            continue
        comp = l.period
        rbt12 = compute_rbt12(view, comp).value
        receita = next((a.receita for a in view.activities(comp) if a.key == l.activity), ZERO)
        faltante = money(max(minimo * rbt12 - l.base, ZERO) / 12)
        if not faltante or not receita:
            continue
        try:
            _, _, ef_v = band_rates("V", rbt12, rules, set(), False)
            _, _, ef_iii = band_rates("III", rbt12, rules, set(), False)
        except Exception:        # RBT12 fora das faixas: sem simulação
            continue
        economia = money(receita * (ef_v - ef_iii))
        salario = faltante / (1 + params.fgts)
        custo_prolabore = money(faltante * params.inss_socio)
        custo_salario = money(salario * (1 + params.fgts + params.provisoes_salario))
        common = dict(kind="informativo", activity=l.activity, verified=params.verified)
        info = {"folha_12m": str(l.base), "rbt12": str(money(rbt12)), "fator_r": str(l.rate.quantize(Decimal("0.0001"))),
                "receita_atividade": str(money(receita)), "tabela": {"versao": params.version, "hash": params.hash[:12]}}
        out.append(Line("SIMPLES", comp, "folha_ideal_economia", faltante, ef_v - ef_iii, economia,
                        f"folha mensal faltante {brl(faltante)} = (28% × RBT12 {brl(rbt12)} − folha 12m {brl(l.base)}) ÷ 12; "
                        f"economia no Anexo III = receita {brl(receita)} × (efetiva V {pct(ef_v, 2)} − efetiva III {pct(ef_iii, 2)})",
                        ref, origin=info, **common))
        out.append(Line("SIMPLES", comp, "folha_ideal_prolabore", faltante, params.inss_socio, custo_prolabore,
                        f"pró-labore adicional {brl(faltante)} × INSS do sócio {pct(params.inss_socio, 2)}",
                        ref, origin={**info, "economia": str(economia), "liquido": str(economia - custo_prolabore)}, **common))
        out.append(Line("SIMPLES", comp, "folha_ideal_salario", money(salario), 1 + params.fgts + params.provisoes_salario,
                        custo_salario,
                        f"salário {brl(salario)} (= {brl(faltante)} ÷ (1 + FGTS {pct(params.fgts, 2)})) × (1 + FGTS + "
                        f"provisões de 13º e férias {pct(params.provisoes_salario, 2)})",
                        ref, origin={**info, "economia": str(economia), "liquido": str(economia - custo_salario)}, **common))
    return out

