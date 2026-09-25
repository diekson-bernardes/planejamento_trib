"""Catálogo de premissas: sugestões com origem (a partir do snapshot e das regras) e leitura das confirmadas."""
import re
from dataclasses import dataclass, field
from decimal import Decimal

from worker.engine.activities import ActivityProfile, declared_zero_taxes, match_profile
from worker.engine.memory import D, ZERO, canonical_hash, money
from worker.engine.rules import RuleSet
from worker.engine.snapshot import SnapshotView, previous_months
from worker.validations import dre_groups, signed_total

CASE = "caso"
LOCAL_TAX_ACCOUNT = re.compile(r"\b(icms|iss)\b")   # conta de ICMS/ISS na DRE (palavra inteira)
DECLARATION_CHOICES = ["nao", "sim", "nao_informado"]


def comp_scope(comp: str) -> str:
    return "competencia:" + comp


def activity_scope(key: str) -> str:
    return "atividade:" + key


@dataclass
class Suggestion:
    key: str
    scope: str
    group: str
    label: str
    value_type: str               # decimal | percent | choice | profile | taxes | boolean
    suggested_value: object       # JSON (números como string) ou None quando não há sugestão
    origin: dict = field(default_factory=dict)
    choices: list | None = None

    def as_row(self) -> dict:
        return {
            "key": self.key, "scope": self.scope, "group": self.group, "label": self.label,
            "value_type": self.value_type, "suggested_value": self.suggested_value,
            "suggested_origin": self.origin, "choices": self.choices,
        }


def _dec(value: Decimal) -> str:
    return str(money(value))


def suggest(view: SnapshotView, rules: RuleSet, confirmed: "Assumptions | None" = None) -> list[Suggestion]:
    """Sugestões do caso. `confirmed` (premissas já confirmadas) mantém as dependentes de perfis alterados
    pelo usuário — ex.: a folha do Fator R quando uma atividade passou a ser sujeita a ele."""
    comps = view.complete_competences()
    out: list[Suggestion] = []

    # ------------------------------------------------------------------ atividades
    seen: dict = {}
    for comp in comps:
        for act in view.activities(comp):
            seen.setdefault(act.key, (comp, act))
    classes = list(rules.presumido["classes"])
    needs_fator_r = False
    for key, (comp, act) in seen.items():
        profile, profile_id = match_profile(act.description, rules)
        effective = (confirmed.profile(key) if confirmed else None) or profile
        needs_fator_r = needs_fator_r or bool(effective and effective.fator_r)
        out.append(Suggestion(
            key="atividade.perfil", scope=activity_scope(key), group="atividades",
            label="Perfil da atividade: " + act.description,
            value_type="profile",
            suggested_value=profile.as_value() if profile else None,
            origin={**act.origin, "rule": rules.ref("atividades", profile_id or "sem_padrao")},
            choices=[{"anexos": sorted(rules.anexos)}, {"presumido": classes}],
        ))
        out.append(Suggestion(
            key="atividade.tributos_zerados", scope=activity_scope(key), group="atividades",
            label="Tributos zerados no Simples (ST/monofásico/exportação): " + act.description,
            value_type="taxes",
            suggested_value=declared_zero_taxes(act, rules),
            origin={**act.origin, "note": "tributos declarados como zero na atividade do PGDAS-D"},
        ))

    # ------------------------------------------------------------------ por competência
    credit_labels = [s.lower() for s in rules.real["sugestao_creditos"]["rotulos"]]
    for comp in comps:
        scope = comp_scope(comp)
        icms_das = view.get("PGDAS_D", comp, "tributo.icms", "icms", "2.8.total_declarado")
        iss_das = view.get("PGDAS_D", comp, "tributo.iss", "iss", "2.8.total_declarado")
        out.append(Suggestion(
            "icms_regime_normal", scope, "icms_iss", f"ICMS no regime normal ({comp}) — Presumido/Real",
            "decimal", _dec(D(icms_das["value"]) if icms_das else ZERO),
            {**view.origin(icms_das), "note": "proxy: ICMS recolhido no DAS; substituir pelo ICMS apurado no regime normal"},
        ))
        out.append(Suggestion(
            "iss_regime_normal", scope, "icms_iss", f"ISS no regime normal ({comp}) — Presumido/Real",
            "decimal", _dec(D(iss_das["value"]) if iss_das else ZERO),
            {**view.origin(iss_das), "note": "proxy: ISS recolhido no DAS; substituir pelo ISS devido no município"},
        ))
        # só contas do grupo de receitas: credora dentro das despesas (ex.: recuperação de vale-transporte) não é receita
        grupo_receitas, _ = dre_groups(view.values("DRE_ALTERDATA", comp))
        outras = [v for v in grupo_receitas if "vendas" not in (v.get("label") or "").lower()]
        out.append(Suggestion(
            "outras_receitas", scope, "receitas", f"Outras receitas tributáveis ({comp}) — financeiras, ganhos",
            "decimal", _dec(signed_total(outras, "C")),
            {"source": "snapshot", "note": "contas do grupo de receitas da DRE exceto vendas",
             "accounts": [v["account_code"] for v in outras]},
        ))
        out.append(Suggestion(
            "pis_cofins_exclusoes", scope, "pis_cofins", f"Exclusões da base de PIS/Cofins ({comp}) — ex.: ICMS destacado",
            "decimal", "0.00", {"source": "padrao", "note": "sem dado de ICMS destacado nos documentos"},
        ))
        credits = [v for v in view.balancete_accounts(comp)
                   if v["section"].startswith("analitica")   # grupos repetiriam o valor das analíticas
                   and v.get("column") == rules.real["sugestao_creditos"]["coluna"]
                   and any(lbl in (v.get("label") or "").lower() for lbl in credit_labels)]
        out.append(Suggestion(
            "pis_cofins_creditos_base", scope, "pis_cofins", f"Base de créditos de PIS/Cofins no Real ({comp})",
            "decimal", _dec(sum((D(v["value"]) for v in credits), ZERO)),
            {"source": "snapshot", "note": "débitos do período nas contas de mercadorias/compras do balancete",
             "accounts": [v["account_code"] for v in credits]},
        ))
        out.append(Suggestion("real.adicoes", scope, "real", f"Adições ao lucro — Real ({comp})",
                              "decimal", "0.00", {"source": "padrao"}))
        out.append(Suggestion("real.exclusoes", scope, "real", f"Exclusões do lucro — Real ({comp})",
                              "decimal", "0.00", {"source": "padrao"}))
        if needs_fator_r:
            series = view.pgdas_series(comp, "folha_anterior")
            months = previous_months(comp, 12)
            folha = sum((series.get(m, ZERO) for m in months), ZERO)
            out.append(Suggestion(
                "folha.folha_12m", scope, "folha", f"Folha de salários dos 12 meses anteriores ({comp}) — Fator R",
                "decimal", _dec(folha) if series else None,
                {"source": "snapshot", "note": "série 2.3 do PGDAS-D" if series else "série 2.3 ausente: informar"},
            ))

    # ------------------------------------------------------------------ caso
    dre_has_icms = any(LOCAL_TAX_ACCOUNT.search((v.get("label") or "").lower())
                       for comp in comps for v in view.dre_accounts(comp))
    out.append(Suggestion("real.icms_iss_ja_na_dre", CASE, "real",
                          "ICMS/ISS já registrados como despesa na DRE (não descontar de novo no Real)",
                          "boolean", dre_has_icms, {"source": "snapshot", "note": "conta de ICMS/ISS na DRE"}))
    out.append(Suggestion("real.saldo_prejuizo_fiscal", CASE, "real", "Saldo de prejuízo fiscal a compensar (início do período)",
                          "decimal", "0.00", {"source": "padrao"}))
    out.append(Suggestion("real.saldo_base_negativa_csll", CASE, "real", "Saldo de base negativa de CSLL (início do período)",
                          "decimal", "0.00", {"source": "padrao"}))
    enc = rules.encargos
    out.append(Suggestion("folha.rat", CASE, "folha", "RAT (1%, 2% ou 3% conforme CNAE)", "percent",
                          enc["rat_sugerido"], {"source": "regra", "rule": rules.ref("encargos", "rat_sugerido")},
                          choices=enc["rat_opcoes"]))
    out.append(Suggestion("folha.fap", CASE, "folha", "FAP (0,5000 a 2,0000)", "decimal",
                          enc["fap_sugerido"], {"source": "regra", "rule": rules.ref("encargos", "fap_sugerido")}))
    out.append(Suggestion("folha.terceiros", CASE, "folha", "Terceiros (Sistema S etc.) — conforme FPAS", "percent",
                          enc["terceiros_por_fpas"][enc["fpas_sugerido"]],
                          {"source": "regra", "rule": rules.ref("encargos", "terceiros_por_fpas", enc["fpas_sugerido"])}))

    latest = comps[-1] if comps else None
    rbaa = view.get("PGDAS_D", latest, "receita.rbaa", "total") if latest else None
    out.append(Suggestion("presumido.receita_total_ano_anterior", CASE, "elegibilidade",
                          "Receita total do ano anterior (limite de R$ 78 mi do Presumido)", "decimal",
                          _dec(D(rbaa["value"])) if rbaa else None,
                          {**view.origin(rbaa), "note": "RBAA do PGDAS-D como aproximação da receita total"}))
    for regime in ("simples", "presumido"):
        for dec in rules.elegibilidade[regime]["declaracoes"]:
            out.append(Suggestion(dec["chave"], CASE, "elegibilidade", dec["pergunta"], "choice",
                                  "nao_informado", {"source": "padrao"}, choices=DECLARATION_CHOICES))
    out += _projection_suggestions(view, comps)
    return out


def _projection_suggestions(view: SnapshotView, comps: list[str]) -> list[Suggestion]:
    """Orçamento dos meses do exercício posteriores à última competência completa (sugerido = média) e
    custo anual de conformidade por regime (exibido à parte, não entra no ranking)."""
    from worker.engine.projection import month_facts, year_months   # projection importa este módulo

    if not comps:
        return []
    facts = [month_facts(view, c) for c in comps]
    receita = sum((f.receita for f in facts), ZERO)
    if not receita:
        return []
    n = Decimal(len(facts))
    media = {"receita": receita / n, "folha": sum((f.empregados for f in facts), ZERO) / n,
             "margem": sum((f.margem * f.receita for f in facts), ZERO) / receita}
    origin = {"source": "snapshot", "note": "média dos meses completos " + ", ".join(comps), "competences": comps}
    out = []
    for comp in (m for m in year_months(int(comps[-1][:4])) if m > comps[-1]):
        scope = comp_scope(comp)
        out.append(Suggestion("projecao.receita", scope, "projecao", f"Receita projetada ({comp}) — orçamento opcional",
                              "decimal", _dec(media["receita"]), origin))
        out.append(Suggestion("projecao.margem", scope, "projecao",
                              f"Margem antes de IRPJ/CSLL projetada ({comp}) — fração da receita",
                              "ratio", str(media["margem"].quantize(Decimal("0.0001"))), origin))
        out.append(Suggestion("projecao.folha", scope, "projecao", f"Folha (base de empregados) projetada ({comp})",
                              "decimal", _dec(media["folha"]), origin))
    for regime, name in (("SIMPLES", "Simples Nacional"), ("PRESUMIDO", "Lucro Presumido"), ("REAL", "Lucro Real")):
        out.append(Suggestion("conformidade.custo_anual", "regime:" + regime, "conformidade",
                              f"Custo anual de conformidade — {name} (exibido à parte, não altera o ranking)",
                              "decimal", "0.00", {"source": "padrao", "note": "informar honorários, obrigações e sistemas"}))
    return out


# ---------------------------------------------------------------------- premissas confirmadas
class Assumptions:
    """Premissas confirmadas: (key, scope) → valor JSON."""

    def __init__(self, rows: list[dict]):
        self.rows = rows
        self._map = {(r["key"], r["scope"]): r["value"] for r in rows}

    def raw(self, key: str, scope: str = CASE):
        return self._map.get((key, scope))

    def decimal(self, key: str, scope: str = CASE, default: Decimal = ZERO) -> Decimal:
        v = self.raw(key, scope)
        return default if v is None else D(v)

    def boolean(self, key: str, scope: str = CASE) -> bool:
        v = self.raw(key, scope)
        return v is True or str(v).lower() in ("true", "sim", "1")

    def text(self, key: str, scope: str = CASE) -> str | None:
        v = self.raw(key, scope)
        return None if v is None else str(v)

    def profile(self, activity_key: str) -> ActivityProfile | None:
        v = self.raw("atividade.perfil", activity_scope(activity_key))
        return ActivityProfile.from_value(v) if isinstance(v, dict) else None

    def zeroed(self, activity_key: str) -> set[str]:
        v = self.raw("atividade.tributos_zerados", activity_scope(activity_key))
        return set(v or [])

    def origin(self, key: str, scope: str = CASE) -> dict:
        return {"source": "assumption", "key": key, "scope": scope}


def assumptions_hash(rows: list[dict]) -> str:
    canonical = sorted(
        ({"key": r["key"], "scope": r["scope"], "value": r["value"]} for r in rows),
        key=lambda r: (r["key"], r["scope"]),
    )
    return canonical_hash(canonical)


def confirm_all_suggested(suggestions: list[Suggestion]) -> list[dict]:
    """Aceita todas as sugestões (uso em testes e em casos dourados)."""
    return [{"key": s.key, "scope": s.scope, "value": s.suggested_value} for s in suggestions]
