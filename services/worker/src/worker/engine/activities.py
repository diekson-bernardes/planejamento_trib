"""Perfil de atividade (anexo, classe de presunção, ST/monofásico, cumulatividade) a partir do PGDAS-D."""
from dataclasses import dataclass

from worker.engine.rules import RuleSet
from worker.engine.snapshot import Activity


@dataclass(frozen=True)
class ActivityProfile:
    anexo: str                  # I..V
    presumido: str              # classe de presunção
    cumulativo_no_real: bool    # receita que permanece no PIS/Cofins cumulativo no Real
    fator_r: bool               # sujeita ao Fator R (III × V)
    exportacao: bool = False

    def as_value(self) -> dict:
        return {
            "anexo": self.anexo,
            "presumido": self.presumido,
            "cumulativo_no_real": self.cumulativo_no_real,
            "fator_r": self.fator_r,
            "exportacao": self.exportacao,
        }

    @staticmethod
    def from_value(value: dict) -> "ActivityProfile":
        return ActivityProfile(
            anexo=str(value["anexo"]),
            presumido=str(value["presumido"]),
            cumulativo_no_real=bool(value.get("cumulativo_no_real", False)),
            fator_r=bool(value.get("fator_r", False)),
            exportacao=bool(value.get("exportacao", False)),
        )


def match_profile(description: str, rules: RuleSet) -> tuple[ActivityProfile | None, str | None]:
    """Primeiro perfil cujos termos obrigatórios aparecem e os proibidos não aparecem."""
    text = description.lower()
    for p in rules.atividades["perfis"]:
        if all(t.lower() in text for t in p["contem"]) and not any(t.lower() in text for t in p["nao_contem"]):
            return ActivityProfile(p["anexo"], p["presumido"], bool(p["cumulativo_no_real"]),
                                   bool(p["fator_r"]), bool(p.get("exportacao", False))), p["id"]
    return None, None


def declared_zero_taxes(activity: Activity, rules: RuleSet) -> list[str]:
    """Tributos declarados como zero na atividade (ST, monofásico, exportação) — sugestão para o Simples."""
    candidates = rules.atividades["tributos_zerados_por_declaracao"]["tributos"]
    anexo_taxes = set()
    profile, _ = match_profile(activity.description, rules)
    if profile:
        anexo_taxes = set(rules.anexos[profile.anexo].taxes)
    out = [
        tax for tax in candidates
        if tax in activity.declared and activity.declared[tax] == 0 and (not anexo_taxes or tax in anexo_taxes)
    ]
    return sorted(set(out))
