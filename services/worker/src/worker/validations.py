"""Validações internas de cada documento (AT-007). Funções puras sobre o ParseResult."""
from collections import defaultdict
from decimal import Decimal

from worker.models import DocType, ExtractedValue, ParseResult, ValidationResult
from worker.pdf.numbers import signed

TOL = Decimal("0.01")
ZERO = Decimal("0")


def check(rule: str, expected: Decimal, actual: Decimal, detail: str | None = None) -> ValidationResult:
    diff = actual - expected
    return ValidationResult(
        rule=rule, status="pass" if abs(diff) <= TOL else "fail",
        expected=expected, actual=actual, diff=diff, detail=detail,
    )


def _get(values: list[ExtractedValue], key: str, section: str | None = None, column: str | None = None) -> Decimal | None:
    for v in values:
        if v.field_key == key and (section is None or v.section == section) and (column is None or v.column == column):
            return v.value
    return None


def validate(result: ParseResult, monthly: bool = True) -> list[ValidationResult]:
    out = [ValidationResult(
        rule="periodo_mensal", status="pass" if monthly else "fail",
        detail=None if monthly else "Período do documento não corresponde a um único mês",
    )]
    fn = {
        DocType.PGDAS_D: _pgdas,
        DocType.FOLHA_ALTERDATA: _folha,
        DocType.DRE_ALTERDATA: _dre,
        DocType.BALANCETE_ALTERDATA: _balancete,
        DocType.LIVRO_ICMS_ALTERDATA: _livro_icms,
    }[result.doc_type]
    return out + fn(result.values)


def _livro_icms(values: list[ExtractedValue]) -> list[ValidationResult]:
    """Por seção (entradas/saídas) e coluna: soma dos CFOPs = totais e soma dos subtotais por origem = totais."""
    out: list[ValidationResult] = []
    for section in ("entradas", "saidas"):
        cols = sorted({v.column for v in values if v.section == section and v.field_key == "total"})
        for col in cols:
            total = _get(values, "total", section=section, column=col)
            cfops = [v.value for v in values if v.section == section and v.column == col and v.field_key.startswith("cfop.")]
            subs = [v.value for v in values if v.section == section and v.column == col and v.field_key.startswith("subtotal.")]
            out.append(check(f"livro.soma_cfop_igual_total[{section}.{col}]", total, sum(cfops, ZERO)))
            if subs:
                out.append(check(f"livro.soma_subtotais_igual_total[{section}.{col}]", total, sum(subs, ZERO)))
    if not out:
        out.append(ValidationResult(rule="livro.totais_presentes", status="fail", detail="Totais de entradas/saídas ausentes"))
    return out


def _pgdas(values: list[ExtractedValue]) -> list[ValidationResult]:
    out: list[ValidationResult] = []
    rpa = _get(values, "receita.rpa", column="total")
    atividades = [v for v in values if v.field_key == "receita_informada"]
    if rpa is not None:
        out.append(check("pgdas.soma_atividades_igual_rpa", rpa, sum((v.value for v in atividades), ZERO)))

    tables: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for v in values:
        if v.field_key.startswith("tributo."):
            tables[v.section][v.column] = v.value
    for section, cols in tables.items():
        parts = sum((val for col, val in cols.items() if col != "total"), ZERO)
        out.append(check("pgdas.tributos_igual_total[" + section + "]", cols.get("total", ZERO), parts))

    for estab in sorted({s.split(".atividade")[0] for s in tables if ".atividade" in s}):
        soma = sum((cols.get("total", ZERO) for s, cols in tables.items() if s.startswith(estab + ".atividade")), ZERO)
        declarado = tables.get(estab + ".total_declarado", {}).get("total")
        if declarado is not None:
            out.append(check("pgdas.soma_atividades_igual_total[" + estab + "]", declarado, soma))

    geral = tables.get("2.8.total_declarado", {}).get("total")
    resumo = _get(values, "resumo.total_debito_declarado")
    if geral is not None and resumo is not None:
        out.append(check("pgdas.total_geral_igual_resumo", resumo, geral))
    exig = tables.get("2.8.total_exigivel", {}).get("total")
    susp = tables.get("2.8.total_suspenso", {}).get("total")
    if geral is not None and exig is not None and susp is not None:
        out.append(check("pgdas.exigivel_mais_suspenso_igual_declarado", geral, exig + susp))
    return out


def _folha(values: list[ExtractedValue]) -> list[ValidationResult]:
    def soma(section: str) -> Decimal:
        return sum((v.value for v in values if v.section == section and v.column == "total"), ZERO)

    out: list[ValidationResult] = []
    adic = _get(values, "total_adicionais", column="total")
    desc = _get(values, "total_descontos", column="total")
    liq = _get(values, "total_liquido", column="total")
    if adic is not None:
        out.append(check("folha.soma_rubricas_igual_total_adicionais", adic, soma("adicionais")))
    if desc is not None:
        out.append(check("folha.soma_rubricas_igual_total_descontos", desc, soma("descontos")))
    if adic is not None and desc is not None and liq is not None:
        out.append(check("folha.adicionais_menos_descontos_igual_liquido", liq, adic - desc))
    return out


def dre_groups(values: list) -> tuple[list, list]:
    """Contas da DRE separadas pelo grupo em que aparecem: antes do total "RECEITAS" → receitas; depois → despesas.

    A natureza não basta: uma conta credora dentro das despesas (ex.: recuperação de vale-transporte) reduz a
    despesa, não é receita. Aceita ExtractedValue ou dicts do snapshot (mesmos campos)."""
    get = (lambda v, k: v[k]) if values and isinstance(values[0], dict) else getattr
    receitas, despesas = [], []
    current = receitas
    for v in values:
        if get(v, "field_key") == "total.RECEITAS":
            current = despesas
        elif get(v, "section") == "conta":
            current.append(v)
    return receitas, despesas


def signed_total(contas: list, positive: str) -> Decimal:
    """Soma com sinal: natureza `positive` soma, a oposta subtrai."""
    get = (lambda v, k: v[k]) if contas and isinstance(contas[0], dict) else getattr
    return sum((Decimal(get(v, "value")) if get(v, "nature") == positive else -Decimal(get(v, "value"))
                for v in contas), ZERO)


def _dre(values: list[ExtractedValue]) -> list[ValidationResult]:
    grupo_receitas, grupo_despesas = dre_groups(values)
    receitas = signed_total(grupo_receitas, "C")
    despesas = signed_total(grupo_despesas, "D")
    out: list[ValidationResult] = []
    r = _get(values, "resultado.receitas")
    d = _get(values, "resultado.despesas_custos")
    lucro = _get(values, "resultado.lucro_liquido")
    if r is not None:
        out.append(check("dre.soma_contas_credoras_igual_receitas", r, receitas))
    if d is not None:
        out.append(check("dre.soma_contas_devedoras_igual_despesas", d, despesas))
    if r is not None and d is not None and lucro is not None:
        out.append(check("dre.receitas_menos_despesas_igual_resultado", lucro, r - d))
    return out


def _balancete(values: list[ExtractedValue]) -> list[ValidationResult]:
    accounts: dict[str, dict[str, ExtractedValue]] = defaultdict(dict)
    for v in values:
        if v.field_key.startswith("conta."):
            accounts[v.account_code][v.column] = v
    failing = []
    for code, cols in accounts.items():
        if len(cols) != 4:
            failing.append(code)
            continue
        esperado = signed(cols["saldo_atual"].value, cols["saldo_atual"].nature)
        calculado = (signed(cols["saldo_anterior"].value, cols["saldo_anterior"].nature)
                     + cols["debito"].value - cols["credito"].value)
        if abs(esperado - calculado) > TOL:
            failing.append(code)
    out = [ValidationResult(
        rule="balancete.saldo_anterior_mais_movimento_igual_saldo_atual",
        status="pass" if not failing else "fail",
        expected=ZERO, actual=Decimal(len(failing)), diff=Decimal(len(failing)),
        detail=("Contas com diferença: " + ", ".join(sorted(failing))) if failing else
        str(len(accounts)) + " contas conferidas",
    )]
    nivel1 = [c for c, cols in accounts.items()
              if cols.get("debito") is not None and cols["debito"].section.endswith(".nivel1")]
    deb = sum((accounts[c]["debito"].value for c in nivel1), ZERO)
    cred = sum((accounts[c]["credito"].value for c in nivel1), ZERO)
    out.append(check("balancete.debitos_igual_creditos", deb, cred))
    rec = _get(values, "periodo.receita")
    desp = _get(values, "periodo.despesa_custo")
    lucro = _get(values, "periodo.lucro")
    if rec is not None and desp is not None and lucro is not None:
        out.append(check("balancete.resultado_do_periodo", lucro, rec - desp))
    return out
