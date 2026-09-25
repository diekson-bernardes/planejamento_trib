"""Leitura do snapshot homologado (conteúdo de `homologate_case`) como fatos por documento e competência."""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from worker.engine.memory import D, ZERO

DOC_TYPES = ("PGDAS_D", "FOLHA_ALTERDATA", "DRE_ALTERDATA", "BALANCETE_ALTERDATA")


def comp_of(value: str | None) -> str | None:
    """'2026-08-01' ou '2026-08' → '2026-08'."""
    return value[:7] if value else None


def previous_months(comp: str, n: int) -> list[str]:
    y, m = int(comp[:4]), int(comp[5:7])
    out = []
    for _ in range(n):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append(f"{y:04d}-{m:02d}")
    return out


ZEROABLE_TAXES = ("icms", "iss", "pis", "cofins", "ipi")


@dataclass(frozen=True)
class Activity:
    key: str             # identificador estável (slug da descrição + tributos declarados zero)
    description: str
    section: str         # ex.: 2.7.estab1.atividade1
    receita: Decimal
    declared: dict       # tributo → valor declarado no PGDAS-D
    origin: dict


class SnapshotView:
    def __init__(self, content: dict):
        self.content = content
        self._index: dict = defaultdict(list)
        for v in content.get("values", []):
            self._index[(v["doc_type"], comp_of(v["competence"]))].append(v)
        self._files = content.get("files", [])

    # ------------------------------------------------------------------ competências
    def competences_with(self, doc_type: str) -> set[str]:
        return {comp_of(f["competence"]) for f in self._files if f.get("doc_type") == doc_type and f.get("competence")}

    def all_competences(self) -> list[str]:
        return sorted({comp_of(f["competence"]) for f in self._files if f.get("competence")})

    def complete_competences(self) -> list[str]:
        sets = [self.competences_with(t) for t in DOC_TYPES]
        return sorted(set.intersection(*sets)) if all(sets) else []

    def excluded_competences(self) -> list[str]:
        complete = set(self.complete_competences())
        return [c for c in self.all_competences() if c not in complete]

    # ------------------------------------------------------------------ fatos
    def values(self, doc_type: str, comp: str) -> list[dict]:
        return self._index.get((doc_type, comp), [])

    def get(self, doc_type: str, comp: str, field_key: str, column: str | None = None,
            section: str | None = None) -> dict | None:
        for v in self.values(doc_type, comp):
            if v["field_key"] == field_key and (column is None or v.get("column") == column) and (
                section is None or v["section"] == section
            ):
                return v
        return None

    def value(self, *args, **kwargs) -> Decimal | None:
        v = self.get(*args, **kwargs)
        return D(v["value"]) if v else None

    @staticmethod
    def origin(v: dict | None) -> dict:
        if not v:
            return {}
        return {
            "source": "snapshot",
            "doc_type": v["doc_type"],
            "competence": comp_of(v["competence"]),
            "field_key": v["field_key"],
            "column": v.get("column"),
            "account_code": v.get("account_code"),
            "file_id": v.get("file_id"),
            "page": v.get("page"),
            "value_id": v.get("id"),
        }

    # ------------------------------------------------------------------ PGDAS-D
    def pgdas_series(self, comp: str, prefix: str) -> dict:
        """Série mensal (competência → valor) interna + externa declarada no PGDAS-D da competência."""
        out: dict = defaultdict(lambda: ZERO)
        for v in self.values("PGDAS_D", comp):
            if v["field_key"].startswith(prefix + "."):
                month = v["field_key"].split(".", 1)[1]
                out[month] += D(v["value"])
        return dict(out)

    def activities(self, comp: str) -> list[Activity]:
        from worker.parsers.base import slug

        by_section: dict = defaultdict(dict)
        for v in self.values("PGDAS_D", comp):
            if ".atividade" not in v["section"]:
                continue
            if v["field_key"] == "receita_informada":
                by_section[v["section"]]["receita"] = v
            elif v["field_key"].startswith("tributo."):
                by_section[v["section"]].setdefault("tributos", {})[v.get("column")] = D(v["value"])
        out = []
        for section in sorted(by_section, key=lambda s: (len(s), s)):
            data = by_section[section]
            rv = data.get("receita")
            if not rv:
                continue
            description = rv.get("label") or section
            declared = data.get("tributos", {})
            # a mesma descrição aparece com e sem ST/monofásico: os tributos zerados distinguem as atividades
            zero = sorted(t for t in ZEROABLE_TAXES if declared.get(t) == 0)
            out.append(Activity(
                key=slug(description)[:80] + ("~zero-" + "-".join(zero) if zero else ""),
                description=description,
                section=section,
                receita=D(rv["value"]),
                declared=declared,
                origin=self.origin(rv),
            ))
        return out

    def dre_accounts(self, comp: str) -> list[dict]:
        return [v for v in self.values("DRE_ALTERDATA", comp) if v["section"] == "conta"]

    def balancete_accounts(self, comp: str) -> list[dict]:
        return [v for v in self.values("BALANCETE_ALTERDATA", comp) if v["field_key"].startswith("conta.")]
