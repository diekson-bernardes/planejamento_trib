"""Planejamento rápido: snapshot homologado (Declaração de Faturamento + folha/DRE em PDF ou digitadas) → conteúdo no
formato do dossiê completo (PGDAS_D/FOLHA/DRE/BALANCETE por mês), lido pelo motor sem alteração.

- Meses "realizados": com faturamento, folha e DRE (PDF ou digitação). A folha e a DRE em PDF são copiadas; as
  digitadas viram valores sintéticos. O PGDAS-D é sintético: RPA = faturamento, séries/RBA/RBAA/RBT12 da declaração.
- Meses anteriores à declaração que entram em RBT12/RBAA recebem a média mensal da declaração (ressalva na origem).
- Atividades sintéticas por CNAE marcado no dossiê (ciclo 6; sem atividades gravadas = CNAE principal com 100%), cada
  uma com a parcela do faturamento informada. ICMS-ST e monofásico continuam frações da receita da empresa, retiradas
  das atividades de comércio (perfil confirmado no Anexo I ou II): variantes normal, com ICMS-ST e monofásico.
- Fator R: a folha dos 12 meses é derivada da folha informada (worker.engine.fator_r), não é premissa editável.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from worker.engine.assumptions import CASE, Assumptions, Suggestion, activity_scope, comp_scope
from worker.engine import fator_r
from worker.engine.cnae import CnaeTable, format_cnae
from worker.engine.memory import D, ZERO, money
from worker.engine.projection import MonthFacts, synthetic_month
from worker.engine.rules import RuleSet
from worker.engine.snapshot import Activity, SnapshotView, previous_months
from worker.parsers.base import slug

DOCS = ("PGDAS_D", "FOLHA_ALTERDATA", "DRE_ALTERDATA", "BALANCETE_ALTERDATA")
GROUP = "rapido"
PCT_ST, PCT_MONO = "rapido.pct_icms_st", "rapido.pct_monofasico"
VARIANTS = (("normal", ()), ("st", ("icms",)), ("mono", ("cofins", "pis")))
REGIMES = ("SIMPLES", "PRESUMIDO", "SIMPLES_HIBRIDO")
DROP_KEYS = ("pis_cofins_creditos_base", "real.adicoes", "real.exclusoes", "real.icms_iss_ja_na_dre",
             "real.saldo_prejuizo_fiscal", "real.saldo_base_negativa_csll", fator_r.FOLHA_KEY)


class QuickCaseError(Exception):
    """Dossiê rápido sem dado mínimo (faturamento, mês com folha e DRE, percentuais inválidos)."""


def is_rapido(content: dict) -> bool:
    return (content.get("case") or {}).get("kind") == "rapido"


def _comp(value: str) -> str:
    return str(value)[:7]


@dataclass
class QuickCase:
    view: SnapshotView
    assumptions: Assumptions | None
    realized: list
    faturamento: dict                          # "AAAA-MM" → receita (declaração ou digitação)
    series: dict                               # meses usados em RBT12/RBAA, inclusive os estimados pela média
    estimated_prior: list = field(default_factory=list)
    activity_keys: dict = field(default_factory=dict)   # variante → chave da atividade sintética (1ª atividade)
    cnae: str | None = None
    activities: list = field(default_factory=list)     # QuickActivity por CNAE marcado
    informed_payroll: dict = field(default_factory=dict)   # mês → (salários, pró-labore) informados


@dataclass(frozen=True)
class QuickActivity:
    cnae: str | None
    descricao: str
    percentual: Decimal                        # 0–100
    keys: dict                                 # variante → chave da atividade sintética


def faturamento(content: dict) -> dict:
    out = {}
    for v in content.get("values", []):
        if v["doc_type"] == "DECLARACAO_FATURAMENTO" and v["field_key"] == "faturamento.mes":
            out[_comp(v["competence"])] = D(v["value"])
    for m in content.get("manual_values", []):
        if m["doc_type"] == "FATURAMENTO" and m["field_key"] == "faturamento.mes":
            out.setdefault(_comp(m["competence"]), D(m["value"]))
    return dict(sorted(out.items()))


def _manual(content: dict, doc: str, comp: str) -> dict:
    return {m["field_key"]: D(m["value"]) for m in content.get("manual_values", [])
            if m["doc_type"] == doc and _comp(m["competence"]) == comp}


def _pdf_values(content: dict, doc: str, comp: str) -> list:
    return [v for v in content.get("values", []) if v["doc_type"] == doc and _comp(v["competence"]) == comp]


def _pct(confirmed: Assumptions | None, key: str) -> Decimal:
    return confirmed.decimal(key) if confirmed is not None and confirmed.raw(key) is not None else ZERO


def case_activities(content: dict) -> list[dict]:
    """Atividades marcadas no dossiê; sem nenhuma, o CNAE principal com 100% (dossiês anteriores ao ciclo 6)."""
    company = content.get("company") or {}
    rows = content.get("activities") or []
    if rows:
        return [{"cnae": r.get("cnae"), "descricao": r.get("descricao") or "", "percentual": D(r["percentual"])}
                for r in rows]
    return [{"cnae": company.get("cnae_principal"), "descricao": company.get("cnae_descricao") or "",
             "percentual": Decimal("100")}]


def activity_templates(content: dict) -> tuple[dict, list]:
    """Atividades sintéticas por CNAE × variante (chave = a que a SnapshotView calcula a partir da descrição)."""
    out, acts = {}, []
    for row in case_activities(content):
        cnae = row["cnae"]
        description = f"CNAE {format_cnae(cnae)} {row['descricao']}".strip() if cnae else "Atividade principal"
        keys = {}
        for variant, zero in VARIANTS:
            declared = {t: (ZERO if t in zero else Decimal("1")) for t in ("irpj", "csll", "cofins", "pis", "inss_cpp", "icms")}
            zero_all = sorted(t for t in ("icms", "iss", "pis", "cofins", "ipi") if declared.get(t) == 0)
            key = slug(description)[:80] + ("~zero-" + "-".join(zero_all) if zero_all else "")
            out[key] = Activity(key, description, f"2.7.estab1.atividade{len(out) + 1}", Decimal("1"), declared,
                                {"source": "rapido", "cnae": cnae})
            keys[variant] = key
        acts.append(QuickActivity(cnae, row["descricao"], row["percentual"], keys))
    return out, acts


def informed_payroll(content: dict) -> dict:
    """Mês → (salários, pró-labore) informados em PDF (Resumo Geral) ou digitados."""
    months = {_comp(v["competence"]) for v in content.get("values", []) if v["doc_type"] == "FOLHA_ALTERDATA"}
    months |= {_comp(m["competence"]) for m in content.get("manual_values", []) if m["doc_type"] == "FOLHA"}
    out = {}
    for comp in sorted(months):
        pdf = {v["field_key"]: D(v["value"]) for v in _pdf_values(content, "FOLHA_ALTERDATA", comp)}
        if pdf:
            emp = pdf.get("aux.base_empregados", pdf.get("fgts.base_sem_13", ZERO))
            out[comp] = (emp, pdf.get("auxiliares.base_socios", ZERO))
        else:
            mf = _manual(content, "FOLHA", comp)
            out[comp] = (mf.get("folha.salarios", ZERO), mf.get("folha.pro_labore", ZERO))
    return out


def _commerce(confirmed: Assumptions | None, act: "QuickActivity") -> bool:
    if confirmed is None:
        return False
    v = confirmed.raw("atividade.perfil", activity_scope(act.keys["normal"]))
    return isinstance(v, dict) and v.get("anexo") in ("I", "II")


def _revenue_split(receita: Decimal, acts: list, confirmed: Assumptions | None, st: Decimal, mono: Decimal) -> dict:
    """Chave → receita do mês. ST/monofásico (frações da receita da empresa) saem das atividades de comércio."""
    bases = [(act, receita * act.percentual / 100) for act in acts]
    commerce = sum((b for act, b in bases if _commerce(confirmed, act)), ZERO)
    if (st or mono) and receita and (st + mono) * receita > commerce:
        raise QuickCaseError("percentuais de ICMS-ST e monofásico maiores que a parcela de comércio (atividades do "
                             "Anexo I ou II)")
    out = {}
    for act, b in bases:
        f = receita / commerce if _commerce(confirmed, act) and commerce else ZERO
        s_st, s_mono = st * f, mono * f
        out[act.keys["normal"]] = b * (1 - s_st - s_mono)
        out[act.keys["st"]] = b * s_st
        out[act.keys["mono"]] = b * s_mono
    return out


def build_quick_case(content: dict, confirmed: Assumptions | None = None) -> QuickCase:
    fat = faturamento(content)
    if not fat:
        raise QuickCaseError("dossiê rápido sem faturamento")
    realized = []
    for comp in fat:
        has_folha = _pdf_values(content, "FOLHA_ALTERDATA", comp) or _manual(content, "FOLHA", comp)
        has_dre = _pdf_values(content, "DRE_ALTERDATA", comp) or _manual(content, "DRE", comp)
        if has_folha and has_dre:
            realized.append(comp)
    if not realized:
        raise QuickCaseError("dossiê rápido sem mês com faturamento, folha e DRE")
    st, mono = _pct(confirmed, PCT_ST), _pct(confirmed, PCT_MONO)
    if st < 0 or mono < 0 or st + mono > 1:
        raise QuickCaseError("percentuais de ICMS-ST e monofásico inválidos (cada um ≥ 0 e soma ≤ 100%)")

    # série de receitas: declaração + meses anteriores necessários (Jan do ano anterior em diante) pela média
    year = int(realized[-1][:4])
    mean = sum(fat.values(), ZERO) / len(fat)
    first = f"{year - 1:04d}-01"
    series, estimated = {}, []
    month = first
    last = max(fat)
    while month <= last:
        if month in fat:
            series[month] = money(fat[month])
        else:
            series[month] = money(mean)
            estimated.append(month)
        y, m = int(month[:4]), int(month[5:7]) + 1
        month = f"{y + (m > 12):04d}-{(m - 1) % 12 + 1:02d}"
    rbaa = sum((series[m] for m in series if m.startswith(f"{year - 1:04d}-")), ZERO)

    templates, acts = activity_templates(content)
    total_pct = sum((a.percentual for a in acts), ZERO)
    if total_pct != 100:
        raise QuickCaseError(f"percentuais das atividades somam {total_pct}%, precisam somar 100%")
    files, values = [], []
    for comp in realized:
        receita = fat[comp]
        pdf_folha, pdf_dre = _pdf_values(content, "FOLHA_ALTERDATA", comp), _pdf_values(content, "DRE_ALTERDATA", comp)
        mf, md = _manual(content, "FOLHA", comp), _manual(content, "DRE", comp)
        lucro = md.get("dre.resultado", ZERO)
        facts = MonthFacts(
            receita=receita, margem=(lucro / receita) if receita else ZERO,
            empregados=mf.get("folha.salarios", ZERO), socios=mf.get("folha.pro_labore", ZERO),
            autonomos=mf.get("folha.autonomos", ZERO),
            activities=_revenue_split(receita, acts, confirmed, st, mono))
        rba = sum((series[m] for m in series if m[:4] == comp[:4] and m < comp), ZERO)
        rbt12 = sum((series.get(m, ZERO) for m in previous_months(comp, 12)), ZERO)
        prior = {m: series[m] for m in series if first <= m < comp}
        month_values = synthetic_month(comp, "realizado", facts, templates,
                                       rba, rbaa, rbt12, prior)
        if pdf_folha:
            month_values = [v for v in month_values if v["doc_type"] != "FOLHA_ALTERDATA"] + pdf_folha
        if pdf_dre:
            month_values = [v for v in month_values if v["doc_type"] != "DRE_ALTERDATA"] + pdf_dre
        values += month_values
        files += [{"id": f"rapido-{doc}-{comp}", "original_name": f"planejamento rapido {doc} {comp}",
                   "doc_type": doc, "competence": comp + "-01", "parser_version": "rapido-1"} for doc in DOCS]
    view = SnapshotView({"schema_version": content.get("schema_version", 1), "company": content.get("company", {}),
                         "files": files, "values": values})
    assumptions = _with_variant_profiles(confirmed, acts) if confirmed is not None else None
    return QuickCase(view, assumptions, realized, fat, series, estimated, dict(acts[0].keys),
                     (content.get("company") or {}).get("cnae_principal"), acts, informed_payroll(content))


def _with_variant_profiles(confirmed: Assumptions, acts: list) -> Assumptions:
    """As variantes ST/monofásico usam o perfil confirmado da própria atividade e zeram os tributos da variante."""
    rows = [dict(r) for r in confirmed.rows]
    have = {(r["key"], r["scope"]) for r in rows}
    for act in acts:
        principal = confirmed.raw("atividade.perfil", activity_scope(act.keys["normal"]))
        for variant, zero in VARIANTS:
            scope = activity_scope(act.keys[variant])
            if variant != "normal" and principal is not None and ("atividade.perfil", scope) not in have:
                rows.append({"key": "atividade.perfil", "scope": scope, "value": principal})
            if ("atividade.tributos_zerados", scope) not in have:
                rows.append({"key": "atividade.tributos_zerados", "scope": scope, "value": sorted(zero)})
    return Assumptions(rows)


def _has_fator_r(confirmed: Assumptions, qc: QuickCase) -> bool:
    for act in qc.activities:
        v = confirmed.raw("atividade.perfil", activity_scope(act.keys["normal"]))
        if isinstance(v, dict) and v.get("fator_r"):
            return True
    return False


def fator_r_adjuster(qc: QuickCase, confirmed: Assumptions, params: fator_r.FatorRParams):
    """Ajuste da projeção com a folha 12m derivada; None quando nenhuma atividade confirmada é sujeita ao Fator R."""
    if not _has_fator_r(confirmed, qc):
        return None
    tratamento = confirmed.raw(fator_r.TRATAMENTO_KEY)
    return fator_r.make_adjuster(qc.informed_payroll, set(qc.realized), max(qc.faturamento),
                                 str(tratamento) if tratamento is not None else None, params)


def rapido_suggestions(content: dict, qc: QuickCase, base: list, rules: RuleSet, cnae: CnaeTable) -> list:
    """Ajusta as sugestões do motor ao dossiê rápido: sem premissas do Real, perfil de cada atividade pelo CNAE,
    percentuais de ST/monofásico, tratamento dos meses sem folha (Fator R), ICMS no regime normal pelo proxy do DAS e
    outras receitas digitadas. A folha 12m do Fator R é derivada no cálculo (fator_r), não é sugerida."""
    from worker.engine.simples import band_rates

    variants = {a.keys[v] for a in qc.activities for v in ("st", "mono")}
    out = []
    for s in base:
        if s.key in DROP_KEYS or s.scope == "regime:REAL" or s.group == "real":
            continue
        if s.scope.removeprefix("atividade:") in variants:
            continue                           # variantes seguem o perfil da principal (_with_variant_profiles)
        if s.key == "reforma.creditos_base":   # sem livro nem balancete: sugestão zero seria crédito falso de 0
            s = Suggestion(s.key, s.scope, s.group, s.label, s.value_type, None,
                           {"source": "rapido", "note": "sem Livro de Apuração nem balancete: informar as compras creditáveis do mês"})
        out.append(s)
    profiles = {}
    for act in qc.activities:
        principal = act.keys["normal"]
        match = cnae.match(act.cnae)
        profile = match.profile.as_value() if match else None
        profiles[principal] = profile
        note = (match.nota + (" — VEDADO ao Simples: confirmar" if match.vedado else "")) if match else "CNAE fora da tabela: escolher o anexo"
        origin = {"source": "cnae", "cnae": act.cnae, "prefixo": match.prefixo if match else None, "note": note,
                  "percentual": str(act.percentual),
                  "tabela": {"versao": cnae.version, "hash": cnae.hash[:12], "verificado": cnae.verified}}
        base_profile = next((s for s in out if s.key == "atividade.perfil" and s.scope == activity_scope(principal)), None)
        out = [s for s in out if s is not base_profile]
        choices = base_profile.choices if base_profile else [{"anexos": sorted(rules.anexos)},
                                                             {"presumido": list(rules.presumido["classes"])}]
        label = f"Perfil da atividade — CNAE {format_cnae(act.cnae)}"
        if len(qc.activities) > 1:
            label += f" ({str(act.percentual).replace('.', ',')}% do faturamento)"
        out.append(Suggestion("atividade.perfil", activity_scope(principal), "atividades", label, "profile", profile,
                              origin, choices))
    with_fator_r = any(p and p.get("fator_r") for p in profiles.values()) or (
        qc.assumptions is not None and _has_fator_r(qc.assumptions, qc))
    if with_fator_r:
        year = int(max(qc.faturamento)[:4]) + 1
        missing = fator_r.missing_months([f"{year:04d}-{m:02d}" for m in range(1, 13)], qc.informed_payroll,
                                         max(qc.faturamento))
        if missing:
            meses = ", ".join(f"{m[5:7]}/{m[:4]}" for m in missing)
            choices = list(fator_r.TRATAMENTOS) if qc.informed_payroll else ["zero"]
            out.append(Suggestion(fator_r.TRATAMENTO_KEY, CASE, "folha",
                                  "Fator R: como tratar os meses sem folha na janela de 12 meses", "choice",
                                  None if len(choices) > 1 else "zero",
                                  {"source": "rapido", "meses_sem_folha": missing,
                                   "note": f"meses sem folha informada: {meses} — completar pela média dos meses "
                                           "informados ou considerar zero"}, choices))
    out.append(Suggestion(PCT_ST, CASE, GROUP, "Parcela da receita com ICMS por substituição tributária (fração)",
                          "ratio", "0.0000", {"source": "padrao", "note": "sem PGDAS-D: informar a parcela com ST"}))
    out.append(Suggestion(PCT_MONO, CASE, GROUP, "Parcela da receita com PIS/Cofins monofásico (fração)",
                          "ratio", "0.0000", {"source": "padrao", "note": "sem PGDAS-D: informar a parcela monofásica"}))
    # ICMS no regime normal: proxy = receita da atividade × efetiva do anexo × repartição de ICMS (mesmo proxy do ciclo 2)
    by_key = {(s.key, s.scope): i for i, s in enumerate(out)}
    for comp in qc.realized:
        receita = qc.faturamento[comp]
        rbt12 = sum((qc.series.get(m, ZERO) for m in previous_months(comp, 12)), ZERO)
        icms = ZERO
        details = []
        for act in qc.activities:
            anexo = (profiles.get(act.keys["normal"]) or {}).get("anexo")
            base = receita * act.percentual / 100
            if not (anexo and anexo in rules.anexos and "icms" in rules.anexos[anexo].taxes):
                details.append("anexo não sugerido" if not anexo else f"anexo {anexo} sem ICMS")
                continue
            try:
                rates, band, efetiva = band_rates(anexo, rbt12, rules, set(), False)
                rate = next((r for t, r, *_ in rates if t == "icms"), ZERO)
                icms += base * rate
                details.append(f"receita {money(base)} × efetiva {efetiva.quantize(Decimal('0.0001'))} × repartição do ICMS "
                               f"(anexo {anexo}, faixa {band.faixa})")
            except Exception as exc:          # RBT12 acima da última faixa: sem sugestão calculada
                details.append(str(exc))
        detail = "; ".join(details)
        s = Suggestion("icms_regime_normal", comp_scope(comp), "icms_iss",
                       f"ICMS no regime normal ({comp}) — Presumido e Simples acima do sublimite", "decimal",
                       str(money(icms)), {"source": "proxy_das", "note": detail})
        i = by_key.get((s.key, s.scope))
        if i is None:
            out.append(s)
        else:
            out[i] = s
        md = _manual(content, "DRE", comp)
        if "dre.outras_receitas" in md:
            s = Suggestion("outras_receitas", comp_scope(comp), "receitas",
                           f"Outras receitas tributáveis ({comp}) — digitadas", "decimal",
                           str(money(md["dre.outras_receitas"])), {"source": "manual"})
            i = by_key.get((s.key, s.scope))
            if i is None:
                out.append(s)
            else:
                out[i] = s
    return out
