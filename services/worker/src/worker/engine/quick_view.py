"""Planejamento rápido: snapshot homologado (Declaração de Faturamento + folha/DRE em PDF ou digitadas) → conteúdo no
formato do dossiê completo (PGDAS_D/FOLHA/DRE/BALANCETE por mês), lido pelo motor sem alteração.

- Meses "realizados": com faturamento, folha e DRE (PDF ou digitação). A folha e a DRE em PDF são copiadas; as
  digitadas viram valores sintéticos. O PGDAS-D é sintético: RPA = faturamento, séries/RBA/RBAA/RBT12 da declaração.
- Meses anteriores à declaração que entram em RBT12/RBAA recebem a média mensal da declaração (ressalva na origem).
- Atividades sintéticas do CNAE principal: normal, com ICMS-ST e monofásico (percentuais confirmados pelo analista).
"""
from dataclasses import dataclass, field
from decimal import Decimal

from worker.engine.assumptions import CASE, Assumptions, Suggestion, activity_scope, comp_scope
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
             "real.saldo_prejuizo_fiscal", "real.saldo_base_negativa_csll")


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
    activity_keys: dict = field(default_factory=dict)   # variante → chave da atividade sintética
    cnae: str | None = None


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


def activity_templates(content: dict) -> dict:
    """Atividades sintéticas do CNAE principal (chave = a que a SnapshotView calcula a partir da descrição)."""
    company = content.get("company") or {}
    cnae = company.get("cnae_principal")
    description = f"CNAE {format_cnae(cnae)} {company.get('cnae_descricao') or ''}".strip() if cnae else "Atividade principal"
    out = {}
    for variant, zero in VARIANTS:
        declared = {t: (ZERO if t in zero else Decimal("1")) for t in ("irpj", "csll", "cofins", "pis", "inss_cpp", "icms")}
        zero_all = sorted(t for t in ("icms", "iss", "pis", "cofins", "ipi") if declared.get(t) == 0)
        key = slug(description)[:80] + ("~zero-" + "-".join(zero_all) if zero_all else "")
        out[variant] = Activity(key, description, f"2.7.estab1.atividade{len(out) + 1}", Decimal("1"), declared,
                                {"source": "rapido", "cnae": cnae})
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
    shares = {"normal": 1 - st - mono, "st": st, "mono": mono}

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

    templates = activity_templates(content)
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
            activities={templates[v].key: receita * shares[v] for v, _ in VARIANTS})
        rba = sum((series[m] for m in series if m[:4] == comp[:4] and m < comp), ZERO)
        rbt12 = sum((series.get(m, ZERO) for m in previous_months(comp, 12)), ZERO)
        prior = {m: series[m] for m in series if first <= m < comp}
        month_values = synthetic_month(comp, "realizado", facts, {t.key: t for t in templates.values()},
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
    assumptions = _with_variant_profiles(confirmed, templates) if confirmed is not None else None
    return QuickCase(view, assumptions, realized, fat, series, estimated,
                     {v: t.key for v, t in templates.items()}, (content.get("company") or {}).get("cnae_principal"))


def _with_variant_profiles(confirmed: Assumptions, templates: dict) -> Assumptions:
    """As variantes ST/monofásico usam o perfil confirmado da atividade principal e zeram os tributos da variante."""
    rows = [dict(r) for r in confirmed.rows]
    have = {(r["key"], r["scope"]) for r in rows}
    principal = confirmed.raw("atividade.perfil", activity_scope(templates["normal"].key))
    for variant, zero in VARIANTS:
        scope = activity_scope(templates[variant].key)
        if variant != "normal" and principal is not None and ("atividade.perfil", scope) not in have:
            rows.append({"key": "atividade.perfil", "scope": scope, "value": principal})
        if ("atividade.tributos_zerados", scope) not in have:
            rows.append({"key": "atividade.tributos_zerados", "scope": scope, "value": sorted(zero)})
    return Assumptions(rows)


def rapido_suggestions(content: dict, qc: QuickCase, base: list, rules: RuleSet, cnae: CnaeTable) -> list:
    """Ajusta as sugestões do motor ao dossiê rápido: sem premissas do Real, perfil pelo CNAE, percentuais de
    ST/monofásico, ICMS no regime normal pelo proxy do DAS e outras receitas digitadas."""
    from worker.engine.simples import band_rates

    principal, variants = qc.activity_keys["normal"], {qc.activity_keys["st"], qc.activity_keys["mono"]}
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
    match = cnae.match(qc.cnae)
    profile = match.profile.as_value() if match else None
    note = (match.nota + (" — VEDADO ao Simples: confirmar" if match.vedado else "")) if match else "CNAE fora da tabela: escolher o anexo"
    origin = {"source": "cnae", "cnae": qc.cnae, "prefixo": match.prefixo if match else None, "note": note,
              "tabela": {"versao": cnae.version, "hash": cnae.hash[:12], "verificado": cnae.verified}}
    base_profile = next((s for s in out if s.key == "atividade.perfil" and s.scope == activity_scope(principal)), None)
    out = [s for s in out if s is not base_profile]
    choices = base_profile.choices if base_profile else [{"anexos": sorted(rules.anexos)},
                                                         {"presumido": list(rules.presumido["classes"])}]
    out.append(Suggestion("atividade.perfil", activity_scope(principal), "atividades",
                          f"Perfil da atividade — CNAE {format_cnae(qc.cnae)}", "profile", profile, origin, choices))
    if profile and profile.get("fator_r"):     # Fator R: folha dos 12 meses pela média dos meses informados
        folhas = [sum((D(v["value"]) for v in qc.view.values("FOLHA_ALTERDATA", c)
                       if v["field_key"] in ("aux.base_empregados", "auxiliares.base_socios")), ZERO) for c in qc.realized]
        media = sum(folhas, ZERO) / len(folhas)
        for comp in qc.realized:
            s = Suggestion("folha.folha_12m", comp_scope(comp), "folha",
                           f"Folha de salários dos 12 meses anteriores ({comp}) — Fator R", "decimal",
                           str(money(media * 12)), {"source": "rapido", "note": "média mensal dos meses informados × 12"})
            out = [x for x in out if (x.key, x.scope) != (s.key, s.scope)] + [s]
    out.append(Suggestion(PCT_ST, CASE, GROUP, "Parcela da receita com ICMS por substituição tributária (fração)",
                          "ratio", "0.0000", {"source": "padrao", "note": "sem PGDAS-D: informar a parcela com ST"}))
    out.append(Suggestion(PCT_MONO, CASE, GROUP, "Parcela da receita com PIS/Cofins monofásico (fração)",
                          "ratio", "0.0000", {"source": "padrao", "note": "sem PGDAS-D: informar a parcela monofásica"}))
    # ICMS no regime normal: proxy = receita sem ST × efetiva do anexo × repartição de ICMS (mesmo proxy do ciclo 2)
    anexo = (profile or {}).get("anexo")
    by_key = {(s.key, s.scope): i for i, s in enumerate(out)}
    for comp in qc.realized:
        receita = qc.faturamento[comp]
        rbt12 = sum((qc.series.get(m, ZERO) for m in previous_months(comp, 12)), ZERO)
        icms = ZERO
        detail = "anexo não sugerido"
        if anexo and anexo in rules.anexos and "icms" in rules.anexos[anexo].taxes:
            try:
                rates, band, efetiva = band_rates(anexo, rbt12, rules, set(), False)
                rate = next((r for t, r, *_ in rates if t == "icms"), ZERO)
                icms = receita * rate
                detail = f"receita {money(receita)} × efetiva {efetiva.quantize(Decimal('0.0001'))} × repartição do ICMS (anexo {anexo}, faixa {band.faixa})"
            except Exception as exc:          # RBT12 acima da última faixa: sem sugestão calculada
                detail = str(exc)
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
