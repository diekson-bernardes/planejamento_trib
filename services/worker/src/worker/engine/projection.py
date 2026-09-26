"""Projeção do exercício: monta jan–dez como snapshot sintético lido pelo motor do ciclo 2 sem alteração.

Origem de cada mês:
- realizado: competência completa do snapshot homologado (copiada; transformada só quando há alavanca de sensibilidade);
- estimado: mês anterior ao primeiro completo — receita pela série do PGDAS-D, demais valores em proporção à receita;
- projetado: mês sem documento — média simples dos meses completos;
- orcamento: mês projetado com valor confirmado diferente da sugestão (premissa projecao.*).
"""
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from worker.engine.assumptions import CASE, Assumptions, comp_scope
from worker.engine.decision_params import DecisionParams
from worker.engine.memory import D, ZERO, money
from worker.engine.snapshot import ZEROABLE_TAXES, SnapshotView, previous_months

DOCS = ("PGDAS_D", "FOLHA_ALTERDATA", "DRE_ALTERDATA", "BALANCETE_ALTERDATA")
ONE = Decimal("1")
REALIZADO, ESTIMADO, PROJETADO, ORCAMENTO = "realizado", "estimado", "projetado", "orcamento"
DECLARED_TAXES = ("irpj", "csll", "cofins", "pis", "inss_cpp") + ZEROABLE_TAXES
PROJECTION_KEYS = ("projecao.receita", "projecao.margem", "projecao.folha")


class ProjectionError(Exception):
    """Dado crítico ausente para projetar (sem competência completa, série de receita incompleta)."""


@dataclass(frozen=True)
class Levers:
    """Alavancas da sensibilidade; os valores padrão reproduzem o cenário base."""
    receita: Decimal = ONE           # multiplica a receita de todos os meses do exercício
    margem: Decimal | None = None    # margem antes de IRPJ/CSLL (absoluta) em todos os meses
    folha: Decimal = ONE             # multiplica as bases da folha
    creditos: Decimal = ONE          # multiplica a base de créditos de PIS/Cofins
    icms_iss: Decimal = ONE          # multiplica ICMS/ISS no regime normal
    cbs: Decimal = ONE               # multiplica a alíquota de CBS (exercícios da Reforma)

    @property
    def is_base(self) -> bool:
        return self == Levers()


@dataclass(frozen=True)
class MonthFacts:
    receita: Decimal
    margem: Decimal                 # (lucro líquido + despesa de Simples) ÷ receita
    empregados: Decimal
    socios: Decimal
    autonomos: Decimal
    activities: dict                # chave → receita


@dataclass
class ProjectedCase:
    year: int
    content: dict
    assumptions: list
    origins: dict                   # "2026-01" → origem
    base: dict = field(default_factory=dict)   # valores de referência (média, margem, razões) para memória e sensibilidade
    plan: dict = field(default_factory=dict)       # mês → MonthFacts usado (após alavancas)
    templates: dict = field(default_factory=dict)  # chave da atividade → Activity modelo (descrição e tributos declarados)
    timeline: dict = field(default_factory=dict)   # mês → receita (centavos), inclusive o ano anterior


def year_months(year: int) -> list[str]:
    return [f"{year:04d}-{m:02d}" for m in range(1, 13)]


def month_facts(view: SnapshotView, comp: str) -> MonthFacts:
    receita = view.value("PGDAS_D", comp, "receita.rpa", "total") or ZERO
    lucro_v = view.get("DRE_ALTERDATA", comp, "resultado.lucro_liquido")
    lucro = D(lucro_v["value"]) if lucro_v else ZERO
    if lucro_v and ("preju" in (lucro_v.get("label") or "").lower() or lucro_v.get("nature") == "D"):
        lucro = -lucro
    simples = next((D(v["value"]) for v in view.dre_accounts(comp)
                    if "simples nacional" in (v.get("label") or "").lower()), ZERO)

    def base(*keys):
        for k in keys:
            v = view.value("FOLHA_ALTERDATA", comp, k)
            if v is not None:
                return v
        return ZERO

    return MonthFacts(
        receita=receita,
        margem=(lucro + simples) / receita if receita else ZERO,
        empregados=base("aux.base_empregados", "fgts.base_sem_13"),
        socios=base("auxiliares.base_socios"),
        autonomos=base("auxiliares.base_autonomos"),
        activities={a.key: a.receita for a in view.activities(comp)},
    )


def revenue_series(view: SnapshotView, realized: list[str], year: int) -> dict:
    """Receita mensal conhecida: séries do PGDAS-D (a declaração mais recente prevalece) + RPA dos meses completos.

    Meses do ano anterior ausentes nas séries recebem a diferença RBAA declarada − meses presentes, em partes iguais."""
    out: dict = {}
    for comp in sorted(view.competences_with("PGDAS_D")):
        out.update(view.pgdas_series(comp, "receita_anterior"))
    for comp in realized:
        out[comp] = view.value("PGDAS_D", comp, "receita.rpa", "total") or ZERO
    prev_year = [f"{year - 1:04d}-{m:02d}" for m in range(1, 13)]
    missing = [m for m in prev_year if m not in out]
    if missing:
        rbaa = view.value("PGDAS_D", realized[-1], "receita.rbaa", "total")
        if rbaa is None:
            raise ProjectionError("série de receitas do ano anterior incompleta e sem RBAA declarada")
        rest = rbaa - sum((out[m] for m in prev_year if m in out), ZERO)
        for m in missing:
            out[m] = rest / len(missing)
    return out


def _row(confirmed: Assumptions, key: str, scope: str) -> dict | None:
    return next((r for r in confirmed.rows if r["key"] == key and r["scope"] == scope), None)


def _budget(confirmed: Assumptions, key: str, comp: str, default: Decimal) -> tuple[Decimal, bool]:
    """Premissa projecao.* do mês: (valor, é orçamento?). Sem premissa → média."""
    row = _row(confirmed, key, comp_scope(comp))
    if row is None or row.get("value") is None:
        return default, False
    value = D(row["value"])
    suggested = row.get("suggested_value")
    return value, suggested is not None and D(suggested) != value


def build_projection(view: SnapshotView, confirmed: Assumptions, params: DecisionParams,
                     levers: Levers = Levers()) -> ProjectedCase:
    realized_all = view.complete_competences()
    if not realized_all:
        raise ProjectionError("nenhuma competência completa (PGDAS-D, folha, DRE e balancete) no snapshot")
    year = int(realized_all[-1][:4])
    months = year_months(year)
    realized = [c for c in realized_all if c in months]
    facts = {c: month_facts(view, c) for c in realized}

    # ---------------------------------------------------------------- referências dos meses completos
    total_rev = sum((f.receita for f in facts.values()), ZERO)
    if not total_rev:
        raise ProjectionError("meses completos sem receita")
    n = Decimal(len(realized))
    avg = MonthFacts(
        receita=total_rev / n,
        margem=sum((f.margem * f.receita for f in facts.values()), ZERO) / total_rev,
        empregados=sum((f.empregados for f in facts.values()), ZERO) / n,
        socios=sum((f.socios for f in facts.values()), ZERO) / n,
        autonomos=sum((f.autonomos for f in facts.values()), ZERO) / n,
        activities={},
    )
    act_rev: dict = defaultdict(lambda: ZERO)
    templates: dict = {}
    for c in realized:
        for act in view.activities(c):
            act_rev[act.key] += act.receita
            templates[act.key] = act
    shares = {k: v / total_rev for k, v in act_rev.items()}
    ratios = {}
    for key in params.proportional_keys:
        present = [c for c in realized if confirmed.raw(key, comp_scope(c)) is not None]
        rev = sum((facts[c].receita for c in present), ZERO)
        ratios[key] = (sum((confirmed.decimal(key, comp_scope(c)) for c in present), ZERO) / rev) if rev else None
    series = revenue_series(view, realized, year)

    # ---------------------------------------------------------------- receita, margem e folha por mês
    plan: dict = {}
    origins: dict = {}
    for comp in months:
        if comp in facts:
            f = facts[comp]
            plan[comp] = f
            origins[comp] = REALIZADO
            continue
        if comp < realized[0] and comp in series:
            origins[comp] = ESTIMADO
            receita = series[comp]
            margem, emp = avg.margem, avg.empregados
        else:
            receita, b1 = _budget(confirmed, "projecao.receita", comp, avg.receita)
            margem, b2 = _budget(confirmed, "projecao.margem", comp, avg.margem)
            emp, b3 = _budget(confirmed, "projecao.folha", comp, avg.empregados)
            origins[comp] = ORCAMENTO if (b1 or b2 or b3) else PROJETADO
        plan[comp] = MonthFacts(receita, margem, emp, avg.socios, avg.autonomos,
                                {k: receita * s for k, s in shares.items()})

    # alavancas
    for comp, f in list(plan.items()):
        r = levers.receita
        plan[comp] = MonthFacts(
            receita=f.receita * r,
            margem=levers.margem if levers.margem is not None else f.margem,
            empregados=f.empregados * levers.folha, socios=f.socios * levers.folha,
            autonomos=f.autonomos * levers.folha,
            activities={k: v * r for k, v in f.activities.items()},
        )
    # valores centavo a centavo, iguais aos gravados no conteúdo: o RBT12 declarado bate com o recalculado
    timeline = {m: money(v) for m, v in series.items()}
    for comp in months:
        timeline[comp] = money(plan[comp].receita)

    # ---------------------------------------------------------------- conteúdo sintético
    files, values = [], []
    rbaa = view.value("PGDAS_D", realized[-1], "receita.rbaa", "total") or ZERO
    for comp in months:
        copy_realized = origins[comp] == REALIZADO and levers.is_base
        if copy_realized:
            for doc in DOCS:
                values += view.values(doc, comp)
            files += [f for f in view.content.get("files", []) if (f.get("competence") or "")[:7] == comp]
            continue
        rba = sum((timeline[m] for m in months if m < comp), ZERO)
        prev12 = previous_months(comp, 12)
        rbt12 = sum((timeline.get(m, ZERO) for m in prev12), ZERO)
        values += _synthetic_month(comp, origins[comp], plan[comp], templates, rba, rbaa, rbt12,
                                   {m: timeline[m] for m in timeline if m < comp and m >= f"{year - 1:04d}-01"})
        files += [{"id": f"proj-{doc}-{comp}", "original_name": f"projecao {doc} {comp}", "doc_type": doc,
                   "competence": comp + "-01", "parser_version": "projecao-" + params.version} for doc in DOCS]

    # ---------------------------------------------------------------- premissas
    rows = []
    per_comp_keys = {r["key"] for r in confirmed.rows if r["scope"].startswith("competencia:")}
    for r in confirmed.rows:
        if not r["scope"].startswith("competencia:"):
            rows.append({"key": r["key"], "scope": r["scope"], "value": r["value"]})
    for comp in months:
        scope = comp_scope(comp)
        receita = plan[comp].receita
        for key in sorted(per_comp_keys - set(PROJECTION_KEYS)):
            if origins[comp] == REALIZADO:
                value = confirmed.decimal(key, scope) if confirmed.raw(key, scope) is not None else None
                if value is not None and key in params.proportional_keys:
                    value = value * levers.receita
            elif key in params.proportional_keys and ratios.get(key) is not None:
                value = ratios[key] * receita
            elif confirmed.raw(key, scope) is not None:
                value = confirmed.decimal(key, scope)
            else:
                present = [confirmed.decimal(key, comp_scope(c)) for c in realized if confirmed.raw(key, comp_scope(c)) is not None]
                value = sum(present, ZERO) / len(present) if present else None
            if value is None:
                continue
            if key in ("icms_regime_normal", "iss_regime_normal"):
                value = value * levers.icms_iss
            elif key == "pis_cofins_creditos_base":
                value = value * levers.creditos
            if origins[comp] == REALIZADO and levers.is_base:
                rows.append({"key": key, "scope": scope, "value": confirmed.raw(key, scope)})
            else:
                rows.append({"key": key, "scope": scope, "value": str(money(value))})

    base = {
        "year": year, "realized": realized,
        "media": {"receita": str(money(avg.receita)), "margem": str(avg.margem.quantize(Decimal("0.000001"))),
                  "folha": str(money(avg.empregados))},
        "razoes": {k: (str(v.quantize(Decimal("0.000001"))) if v is not None else None) for k, v in ratios.items()},
        "receita_anual": str(money(sum((plan[c].receita for c in months), ZERO))),
        "folha_anual": str(money(sum((plan[c].empregados + plan[c].socios + plan[c].autonomos for c in months), ZERO))),
        "margem_anual": str((sum((plan[c].margem * plan[c].receita for c in months), ZERO)
                             / sum((plan[c].receita for c in months), ZERO)).quantize(Decimal("0.000001"))),
    }
    return ProjectedCase(year, {"schema_version": view.content.get("schema_version", 1),
                                "company": view.content.get("company", {}), "files": files, "values": values},
                         rows, origins, base, plan, templates, timeline)


def shift_year(pc: ProjectedCase, params: DecisionParams, growth: Decimal, levers: Levers = Levers()) -> ProjectedCase:
    """Exercício seguinte a partir da projeção `pc`: 12 meses com receita × (1 + crescimento) e grandezas proporcionais
    (atividades, lucro pela mesma margem, folha, premissas proporcionais); RBT12/RBA/RBAA a partir da linha do tempo."""
    year = pc.year + 1
    factor = ONE + growth
    months = year_months(year)
    source = {m: f"{pc.year:04d}-{m[5:7]}" for m in months}
    plan: dict = {}
    for m in months:
        f = pc.plan[source[m]]
        plan[m] = MonthFacts(f.receita * factor, f.margem, f.empregados * factor, f.socios * factor,
                             f.autonomos * factor, {k: v * factor for k, v in f.activities.items()})
    timeline = dict(pc.timeline)
    for m in months:
        timeline[m] = money(plan[m].receita)
    rbaa = sum((timeline[m] for m in year_months(pc.year)), ZERO)

    files, values = [], []
    for m in months:
        rba = sum((timeline[x] for x in months if x < m), ZERO)
        rbt12 = sum((timeline.get(x, ZERO) for x in previous_months(m, 12)), ZERO)
        prior = {x: timeline[x] for x in timeline if f"{pc.year:04d}-01" <= x < m}
        values += _synthetic_month(m, PROJETADO, plan[m], pc.templates, rba, rbaa, rbt12, prior)
        files += [{"id": f"proj-{doc}-{m}", "original_name": f"projecao {doc} {m}", "doc_type": doc,
                   "competence": m + "-01", "parser_version": "projecao-" + params.version} for doc in DOCS]

    rows = []
    realized = pc.base.get("realized", [])
    # receita realizada sem a alavanca de receita: a base de créditos acompanha a receita (como em
    # campos_proporcionais_a_receita), então a razão créditos/receita é a do dado, não a do cenário
    rev_realized = sum((pc.plan[c].receita for c in realized), ZERO) / levers.receita
    credits = [Decimal(str(r["value"])) for r in pc.assumptions
               if r["key"] == "reforma.creditos_base" and r["scope"].removeprefix("competencia:") in realized]
    credit_ratio = sum(credits, ZERO) / rev_realized if credits and rev_realized else ZERO
    for r in pc.assumptions:
        scope = r["scope"]
        if not scope.startswith("competencia:"):
            value = r["value"]
            if r["key"] == "reforma.cbs_aliquota" and value is not None and levers.cbs != ONE:
                value = str(Decimal(str(value)) * levers.cbs)
            rows.append({"key": r["key"], "scope": scope, "value": value})
            continue
        comp = scope.removeprefix("competencia:")
        if comp[:4] != f"{pc.year:04d}" or r["key"] == "reforma.creditos_base":
            continue
        value = Decimal(str(r["value"]))
        if r["key"] in params.proportional_keys:
            value = value * factor
        rows.append({"key": r["key"], "scope": "competencia:" + str(year) + comp[4:], "value": str(money(value))})
    for m in months:
        rows.append({"key": "reforma.creditos_base", "scope": "competencia:" + m,
                     "value": str(money(credit_ratio * plan[m].receita * levers.creditos))})

    base = {
        "year": year, "realized": [], "ano_base": pc.year, "crescimento": str(growth),
        "origem_ano_base": {m: pc.origins[source[m]] for m in months},
        "razao_creditos": str(credit_ratio.quantize(Decimal("0.000001"))),
        "receita_anual": str(money(sum((plan[m].receita for m in months), ZERO))),
        "folha_anual": str(money(sum((plan[m].empregados + plan[m].socios + plan[m].autonomos for m in months), ZERO))),
        "margem_anual": pc.base["margem_anual"],
    }
    return ProjectedCase(year, {"schema_version": pc.content.get("schema_version", 1), "company": pc.content.get("company", {}),
                                "files": files, "values": values},
                         rows, {m: PROJETADO for m in months}, base, plan, pc.templates, timeline)


def _v(comp: str, origin: str, doc: str, ordinal: int, section: str, field_key: str, value: Decimal,
       column=None, label=None, account_code=None, nature=None) -> dict:
    return {
        "id": f"proj-{doc}-{comp}-{ordinal}", "file_id": f"proj-{doc}-{comp}", "ordinal": ordinal,
        "doc_type": doc, "competence": comp + "-01", "section": section, "field_key": field_key,
        "label": label, "account_code": account_code, "column": column, "value": str(money(value)),
        "original_value": str(money(value)), "adjusted": False, "nature": nature, "page": None, "bbox": None,
        "projecao": {"origem": origin},
    }


def _synthetic_month(comp: str, origin: str, f: MonthFacts, templates: dict, rba: Decimal, rbaa: Decimal,
                     rbt12: Decimal, prior: dict) -> list[dict]:
    out, n = [], 0

    def add(doc, section, key, value, **kw):
        nonlocal n
        n += 1
        out.append(_v(comp, origin, doc, n, section, key, value, **kw))

    # PGDAS-D: receitas, séries e atividades com o padrão de tributos declarados (ST/monofásico preservados)
    for key, value in (("receita.rpa", f.receita), ("receita.rba", rba), ("receita.rbaa", rbaa), ("receita.rbt12", rbt12)):
        add("PGDAS_D", "2.1", key, value, column="total")
    for month, value in sorted(prior.items()):
        add("PGDAS_D", "2.2.1", "receita_anterior." + month, value, column="mercado_interno")
    for i, (key, receita) in enumerate(sorted(f.activities.items()), start=1):
        tpl = templates[key]
        section = f"2.7.estab1.atividade{i}"
        add("PGDAS_D", section, "receita_informada", receita, label=tpl.description)
        scale = receita / tpl.receita if tpl.receita else ZERO
        for tax in DECLARED_TAXES:
            declared = tpl.declared.get(tax)
            if declared is None:
                continue
            value = ZERO if declared == 0 else max(declared * scale, Decimal("0.01"))
            add("PGDAS_D", section, "tributo." + tax, value, column=tax)
    # folha
    add("FOLHA_ALTERDATA", "auxiliares", "aux.base_empregados", f.empregados)
    add("FOLHA_ALTERDATA", "auxiliares", "auxiliares.base_socios", f.socios)
    add("FOLHA_ALTERDATA", "auxiliares", "auxiliares.base_autonomos", f.autonomos)
    # DRE: lucro antes de IRPJ/CSLL e sem despesa de Simples (a reclassificação do Real soma zero)
    lucro = f.receita * f.margem
    add("DRE_ALTERDATA", "conta", "conta.simples", ZERO, label="Simples Nacional", nature="D")
    add("DRE_ALTERDATA", "resultado", "resultado.lucro_liquido", abs(lucro),
        label="Lucro líquido do exercício" if lucro >= 0 else "Prejuízo do exercício",
        nature=None if lucro >= 0 else "D")
    return out
