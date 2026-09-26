"""Conciliação entre fontes por competência (regras R1–R7). Funções puras.

Cada regra compara um valor de referência (lado A) com uma ou mais fontes contábeis (lado B).
A regra fica `divergent` se qualquer fonte B disponível diferir de A além da tolerância e
`missing_source` se A ou todas as fontes B estiverem ausentes.
"""
from dataclasses import dataclass
from decimal import Decimal

from worker.models import DocType, ReconciliationResult

TARGETS = ("vendas", "simples_despesa", "simples_a_recolher", "inss_a_pagar", "fgts_a_pagar", "salarios_a_pagar",
           "compras_mercadorias")
# Compras para comercialização no Livro de Apuração (mesma lista de rules/2027/consumo.json: cfop_compras_mercadorias)
COMPRAS_CFOP = ("1102", "2102", "1403", "2403")


@dataclass(frozen=True)
class Fact:
    doc_type: DocType
    competence: str  # YYYY-MM
    field_key: str
    column: str | None
    section: str
    value: Decimal  # valor efetivo (original ou ajustado)
    nature: str | None = None


def previous_competence(comp: str) -> str:
    year, month = int(comp[:4]), int(comp[5:7])
    year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return f"{year:04d}-{month:02d}"


class Facts:
    def __init__(self, facts: list[Fact]):
        self._facts = facts

    def competences(self) -> list[str]:
        return sorted({f.competence for f in self._facts})

    def get(self, doc_type: DocType, comp: str, key: str, column: str | None = None,
            section: str | None = None) -> Fact | None:
        for f in self._facts:
            if (f.doc_type == doc_type and f.competence == comp and f.field_key == key
                    and (column is None or f.column == column)
                    and (section is None or f.section == section)):
                return f
        return None

    def value(self, *args, **kwargs) -> Decimal | None:
        f = self.get(*args, **kwargs)
        return f.value if f else None


def _balancete_movement(facts: Facts, comp: str, code: str | None, kind: str) -> Decimal | None:
    if not code:
        return None
    key = "conta." + code
    debit = facts.value(DocType.BALANCETE_ALTERDATA, comp, key, "debito")
    credit = facts.value(DocType.BALANCETE_ALTERDATA, comp, key, "credito")
    if debit is None or credit is None:
        return None
    return {"credito": credit, "debito": debit, "credito_liquido": credit - debit}[kind]


def _rule(comp: str, rule: str, description: str, left_label: str, left: Decimal | None,
          rights: list[tuple[str, Decimal | None]], tolerance: Decimal) -> ReconciliationResult:
    available = [(label, v) for label, v in rights if v is not None]
    details = {"sources": [{"label": label, "value": str(v) if v is not None else None} for label, v in rights]}
    right_label = " / ".join(label for label, _ in rights)
    if left is None or not available:
        return ReconciliationResult(
            competence=comp, rule=rule, description=description, left_label=left_label,
            left_value=left, right_label=right_label,
            right_value=available[0][1] if available else None,
            diff=None, tolerance=tolerance, status="missing_source", details=details,
        )
    diffs = [(label, v, left - v) for label, v in available]
    worst = max(diffs, key=lambda d: abs(d[2]))
    details["diffs"] = [{"label": label, "diff": str(d)} for label, _, d in diffs]
    return ReconciliationResult(
        competence=comp, rule=rule, description=description, left_label=left_label, left_value=left,
        right_label=worst[0], right_value=worst[1], diff=worst[2], tolerance=tolerance,
        status="ok" if abs(worst[2]) <= tolerance else "divergent", details=details,
    )


def reconcile(facts: Facts, mappings: dict[tuple[str, str], str], tolerance: Decimal) -> list[ReconciliationResult]:
    """`mappings[(target, doc_type)] = account_code` já resolvido para a empresa do dossiê."""
    def code(target: str, doc_type: DocType) -> str | None:
        return mappings.get((target, doc_type.value))

    dre = DocType.DRE_ALTERDATA
    bal = DocType.BALANCETE_ALTERDATA
    out: list[ReconciliationResult] = []
    for comp in facts.competences():
        pgdas_rpa = facts.value(DocType.PGDAS_D, comp, "receita.rpa", "total")
        pgdas_das = facts.value(DocType.PGDAS_D, comp, "tributo.total", "total", "2.8.total_declarado")
        dre_vendas = facts.value(dre, comp, "conta." + (code("vendas", dre) or "?"))
        dre_simples = facts.value(dre, comp, "conta." + (code("simples_despesa", dre) or "?"))

        out.append(_rule(comp, "R1", "Receita bruta do mês", "PGDAS-D: receita do PA (RPA)", pgdas_rpa, [
            ("DRE: vendas", dre_vendas),
            ("Balancete: vendas (crédito − débito)", _balancete_movement(facts, comp, code("vendas", bal), "credito_liquido")),
        ], tolerance))
        out.append(_rule(comp, "R2", "DAS da competência", "PGDAS-D: total do débito declarado", pgdas_das, [
            ("DRE: despesa Simples Nacional", dre_simples),
            ("Balancete: débito da despesa Simples Nacional", _balancete_movement(facts, comp, code("simples_despesa", bal), "debito")),
        ], tolerance))
        out.append(_rule(comp, "R3", "INSS dos empregados", "Folha: INSS empregados (GPS)",
                         facts.value(DocType.FOLHA_ALTERDATA, comp, "gps.empregados"), [
            ("Balancete: crédito em INSS a Pagar", _balancete_movement(facts, comp, code("inss_a_pagar", bal), "credito")),
        ], tolerance))
        out.append(_rule(comp, "R4", "FGTS do mês", "Folha: total FGTS apurado",
                         facts.value(DocType.FOLHA_ALTERDATA, comp, "fgts.apurado"), [
            ("Balancete: crédito em FGTS a Pagar", _balancete_movement(facts, comp, code("fgts_a_pagar", bal), "credito")),
        ], tolerance))
        out.append(_rule(comp, "R5", "Proventos da folha", "Folha: total de adicionais",
                         facts.value(DocType.FOLHA_ALTERDATA, comp, "total_adicionais", "total"), [
            ("Balancete: crédito em Salários a Pagar", _balancete_movement(facts, comp, code("salarios_a_pagar", bal), "credito")),
        ], tolerance))
        prev = previous_competence(comp)
        saldo = None
        c6 = code("simples_a_recolher", bal)
        if c6:
            f = facts.get(bal, comp, "conta." + c6, "saldo_anterior")
            saldo = f.value if f else None
        out.append(_rule(comp, "R6", "DAS do mês anterior provisionado",
                         "PGDAS-D " + prev[5:] + "/" + prev[:4] + ": total do débito declarado",
                         facts.value(DocType.PGDAS_D, prev, "tributo.total", "total", "2.8.total_declarado"), [
            ("Balancete: saldo anterior de Simples a Recolher", saldo),
        ], tolerance))
        # R7 só quando há Livro de Apuração na competência (documento opcional)
        livro = [facts.value(DocType.LIVRO_ICMS_ALTERDATA, comp, "cfop." + c, "valor_contabil", "entradas")
                 for c in COMPRAS_CFOP]
        if facts.get(DocType.LIVRO_ICMS_ALTERDATA, comp, "total", "valor_contabil", "entradas") is not None:
            compras = sum((v for v in livro if v is not None), Decimal("0"))
            out.append(_rule(comp, "R7", "Compras para comercialização", "Livro de Apuração: CFOP 1102/2102/1403/2403",
                             compras, [
                ("Balancete: débito em Compras de Mercadorias",
                 _balancete_movement(facts, comp, code("compras_mercadorias", bal), "debito")),
            ], tolerance))
    return out
