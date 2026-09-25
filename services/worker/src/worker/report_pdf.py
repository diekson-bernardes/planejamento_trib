"""PDF executivo da recomendação (ReportLab, modo invariant: mesma entrada → mesmos bytes → mesmo SHA-256).

Formato do comparativo inspirado no SPTE (resultado mensal por regime, observações e comparativo final) +
seções do PRD §10.3 e §15: data-base normativa, premissas, ressalvas, sensibilidade e responsável técnico.
"""
import hashlib
from dataclasses import dataclass
from datetime import timezone
from decimal import Decimal
from io import BytesIO

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

rl_config.invariant = 1

REGIME_NAME = {"SIMPLES": "Simples Nacional", "PRESUMIDO": "Lucro Presumido", "REAL": "Lucro Real"}
REGIMES = ("SIMPLES", "PRESUMIDO", "REAL")
TAX_ORDER = ("irpj", "adicional_irpj", "csll", "cofins", "pis", "cpp", "rat", "terceiros", "icms", "iss", "ipi")
TAX_LABEL = {"irpj": "IRPJ", "adicional_irpj": "Adic. IRPJ", "csll": "CSLL", "cofins": "COFINS", "pis": "PIS",
             "cpp": "CPP", "rat": "RAT", "terceiros": "Terceiros", "icms": "ICMS", "iss": "ISS", "ipi": "IPI"}
MONTHS = ("JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ")
ORIGIN_ABBR = {"realizado": "R", "estimado": "E", "projetado": "P", "orcamento": "O"}
STATUS_LABEL = {"recomendado": "Recomendado", "inconclusivo": "Resultado inconclusivo", "bloqueado": "Bloqueado"}
ROBUSTNESS = {"robusta": "robusta", "atencao": "atenção", "fragil": "frágil"}
EVENT_LABEL = {"created": "Elaborada", "submitted": "Enviada para revisão", "returned": "Devolvida",
               "approved": "Aprovada", "emission_requested": "Emissão solicitada", "emitted": "Emitida",
               "reset_by_assumption": "Voltou a rascunho (premissa alterada)"}


@dataclass(frozen=True)
class ReportData:
    recommendation_id: str
    office_name: str
    legal_name: str
    cnpj: str
    year: int
    rules_version: str
    rules_hash: str
    decision_version: str
    decision_hash: str
    snapshot_sha256: str
    result_hash: str
    threshold: Decimal
    result: dict
    sensitivity: list
    computed: dict
    assumptions: list
    lines: list
    events: list
    approver_name: str
    approver_crc: str
    approved_at: str          # dd/mm/aaaa hh:mm (UTC) — data do registro de aprovação


def brl(value) -> str:
    q = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    sign = "-" if q < 0 else ""
    integer, _, cents = f"{abs(q):.2f}".partition(".")
    groups = []
    while integer:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    return f"{sign}{'.'.join(groups)},{cents}"


def pct(value, places: int = 2) -> str:
    if value is None:
        return "—"
    return f"{Decimal(str(value)) * 100:.{places}f}".replace(".", ",") + "%"


def cnpj_fmt(c: str) -> str:
    d = "".join(ch for ch in (c or "") if ch.isdigit())
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}" if len(d) == 14 else (c or "")


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=15, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=11, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("b", parent=ss["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11),
        "small": ParagraphStyle("s", parent=ss["BodyText"], fontName="Helvetica", fontSize=7, leading=9),
        "cell": ParagraphStyle("c", parent=ss["BodyText"], fontName="Helvetica", fontSize=6.5, leading=8),
    }


def _table(data, widths=None, header_rows=1, font=6.5, align_right_from=1):
    t = Table(data, colWidths=widths, repeatRows=header_rows)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", font),
        ("FONT", (0, 0), (-1, header_rows - 1), "Helvetica-Bold", font),
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor("#E2E8F0")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94A3B8")),
        ("ALIGN", (align_right_from, header_rows), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    return t


def _monthly(d: ReportData, regime: str) -> list:
    months = [f"{d.year:04d}-{m:02d}" for m in range(1, 13)]
    quarters = [f"{d.year:04d}-T{q}" for q in range(1, 5)]
    grid: dict = {}
    for l in d.lines:
        if l["regime"] != regime or l["kind"] != "tributo":
            continue
        grid.setdefault(l["tax"], {}).setdefault(l["period"], Decimal("0"))
        grid[l["tax"]][l["period"]] += Decimal(str(l["amount"]))
    periods = months + (quarters if regime != "SIMPLES" else [])
    header = ["TRIBUTO"] + list(MONTHS) + (["T1", "T2", "T3", "T4"] if regime != "SIMPLES" else []) + ["TOTAL"]
    origins = d.result.get("origins", {})
    rows = [header, ["Origem"] + [ORIGIN_ABBR.get(origins.get(m), "") for m in months]
            + (["", "", "", ""] if regime != "SIMPLES" else []) + [""]]
    col_total = {p: Decimal("0") for p in periods}
    for tax in [t for t in TAX_ORDER if t in grid] + sorted(t for t in grid if t not in TAX_ORDER):
        vals = [grid[tax].get(p, Decimal("0")) for p in periods]
        for p, v in zip(periods, vals):
            col_total[p] += v
        rows.append([TAX_LABEL.get(tax, tax.upper())] + [brl(v) if v else "0" for v in vals] + [brl(sum(vals))])
    rows.append(["TOTAL"] + [brl(col_total[p]) for p in periods] + [brl(sum(col_total.values()))])
    return rows


def story_for(d: ReportData) -> list:
    st = _styles()
    sim = d.result.get("simulation", {})
    regimes = sim.get("regimes", {})
    rec = d.computed
    story = [
        Paragraph(f"Planejamento tributário — exercício {d.year}", st["title"]),
        Paragraph(f"<b>{d.legal_name}</b> · CNPJ {cnpj_fmt(d.cnpj)} · Escritório: {d.office_name}", st["body"]),
        Paragraph(f"Data-base normativa: regras {d.rules_version} (exercício {d.year}) · política de decisão "
                  f"{d.decision_version} · limiar de inconclusivo {pct(d.threshold)}", st["body"]),
        Spacer(1, 3 * mm),
        Paragraph("Recomendação", st["h2"]),
        Paragraph(f"<b>{STATUS_LABEL.get(rec.get('status'), rec.get('status'))}.</b> {rec.get('texto', '')}", st["body"]),
    ]
    if rec.get("fatores"):
        story.append(Paragraph("<b>Principais fatores econômicos:</b>", st["body"]))
        for f in rec["fatores"]:
            story.append(Paragraph("• " + f["texto"], st["body"]))
    econ = []
    if rec.get("economia_vs_segundo") is not None:
        econ.append(f"economia vs. segundo colocado: R$ {brl(rec['economia_vs_segundo'])} ({pct(rec.get('economia_vs_segundo_pct'))})")
    if rec.get("economia_vs_atual") is not None:
        econ.append(f"economia vs. regime atual ({REGIME_NAME.get(rec.get('regime_atual'), '—')}): R$ {brl(rec['economia_vs_atual'])}")
    if econ:
        story.append(Paragraph("<b>Economia estimada:</b> " + "; ".join(econ) + ".", st["body"]))
    for ex in rec.get("excluidos", []):
        story.append(Paragraph(f"<b>{REGIME_NAME[ex['regime']]} fora do ranking</b> ({ex['motivo']}): "
                               + "; ".join(str(x) for x in ex.get("detalhe") or []), st["body"]))

    # ---------------------------------------------------------------- comparativo (formato SPTE)
    story.append(Paragraph("Comparativo do exercício", st["h2"]))
    cols = [t for t in TAX_ORDER if any(Decimal(regimes.get(r, {}).get("by_tax", {}).get(t, "0") or "0") for r in REGIMES)]
    data = [["Regime"] + [TAX_LABEL[t] for t in cols] + ["TOTAL", "Alíq. efetiva", "Conformidade*"]]
    for r in REGIMES:
        rr = regimes.get(r, {})
        if rr.get("status") != "calculado":
            data.append([REGIME_NAME[r]] + ["—"] * len(cols) + ["não calculado", "—", "—"])
            continue
        data.append([REGIME_NAME[r]] + [brl(rr.get("by_tax", {}).get(t, "0")) for t in cols] + [
            brl(rr.get("total")), pct(rec.get("aliquota_efetiva", {}).get(r)),
            ("R$ " + brl(rec["conformidade"][r])) if r in rec.get("conformidade", {}) else "—"])
    story.append(_table(data, font=7))
    winner = rec.get("regime")
    if rec.get("status") == "recomendado" and winner:
        story.append(Paragraph(f"O regime tributário com maior vantagem é o <b>{REGIME_NAME[winner].upper()}</b>.", st["body"]))
    elif rec.get("status") == "inconclusivo":
        story.append(Paragraph("Resultado inconclusivo: diferença entre os dois primeiros abaixo do limiar do escritório.", st["body"]))
    story.append(Paragraph("* Custo de conformidade informado pelo escritório; exibido à parte, não altera a ordem dos regimes.", st["small"]))
    carga = rec.get("carga", {})
    if carga:
        story.append(Spacer(1, 2 * mm))
        story.append(_table([["Carga por natureza", "Consumo", "Renda", "Folha"]] + [
            [REGIME_NAME[r], brl(carga[r]["consumo"]), brl(carga[r]["renda"]), brl(carga[r]["folha"])]
            for r in REGIMES if r in carga], font=7))

    # ---------------------------------------------------------------- sensibilidade
    story.append(Paragraph("Sensibilidade e ponto de virada", st["h2"]))
    sens_rows = [["Variável", "Cenário base", "Ponto de virada", "Novo líder", "Distância", "Robustez", "Limite jurídico"]]
    for s in d.sensitivity:
        money_kind = s["tipo"] == "multiplicador"
        base = ("R$ " + brl(s["base_valor"])) if money_kind else pct(s["base_valor"])
        turn = "sem virada no intervalo" if s["sem_virada"] else (
            ("R$ " + brl(s["virada_valor"])) if money_kind else pct(s["virada_valor"]))
        legal = "—" if s.get("limite_juridico_valor") is None else (
            ("R$ " + brl(s["limite_juridico_valor"])) if money_kind else pct(s["limite_juridico_valor"]))
        sens_rows.append([s["rotulo"], base, turn, REGIME_NAME.get(s.get("novo_lider"), "—"),
                          pct(s.get("distancia"), 1), ROBUSTNESS.get(s.get("robustez"), "—"), legal])
    story.append(_table(sens_rows, font=7))
    story.append(Paragraph("Robustez pela distância do cenário base até a virada: acima de 20% robusta; de 5% a 20% "
                           "atenção; abaixo de 5% frágil. Limite jurídico: valor em que a elegibilidade de um regime muda.",
                           st["small"]))

    # ---------------------------------------------------------------- resultado mensal por regime
    story.append(PageBreak())
    story.append(Paragraph("Resultado mensal por regime", st["h2"]))
    story.append(Paragraph("Origem do mês: R = realizado (documentos homologados), E = estimado (receita do PGDAS-D e "
                           "demais valores proporcionais), P = projetado (média dos meses completos), O = orçamento informado. "
                           "IRPJ/CSLL do Presumido e do Real são trimestrais (colunas T1–T4).", st["small"]))
    for r in REGIMES:
        if regimes.get(r, {}).get("status") != "calculado":
            continue
        story.append(KeepTogether([Paragraph(f"Resultado: {REGIME_NAME[r]}", st["body"]), _table(_monthly(d, r), font=6),
                                   Spacer(1, 3 * mm)]))

    # ---------------------------------------------------------------- premissas, ressalvas e responsável
    story.append(Paragraph("Premissas", st["h2"]))
    prem = [["Premissa", "Escopo", "Valor", "Justificativa"]]
    for a in d.assumptions:
        prem.append([Paragraph(str(a.get("label") or a["key"]), st["cell"]), a["scope"],
                     Paragraph(str(a.get("value")), st["cell"]), Paragraph(a.get("justification") or "", st["cell"])])
    story.append(_table(prem, widths=[110 * mm, 40 * mm, 45 * mm, 70 * mm], align_right_from=99))
    story.append(Paragraph("Ressalvas", st["h2"]))
    for c in rec.get("ressalvas", []):
        story.append(Paragraph("• " + c, st["body"]))
    story.append(Paragraph("Responsável técnico e registro", st["h2"]))
    story.append(Paragraph(f"Aprovado por <b>{d.approver_name}</b> — CRC {d.approver_crc}, em {d.approved_at} (UTC).",
                           st["body"]))
    trail = "; ".join(f"{EVENT_LABEL.get(e['event'], e['event'])}" + (f" ({e['comment']})" if e.get("comment") else "")
                      for e in d.events)
    story.append(Paragraph("Histórico: " + trail + ".", st["small"]))
    story.append(Paragraph(f"Recomendação {d.recommendation_id} · snapshot {d.snapshot_sha256} · resultado {d.result_hash} "
                           f"· regras {d.rules_hash[:16]}… · decisão {d.decision_hash[:16]}…", st["small"]))
    return story


def build_recommendation_pdf(d: ReportData) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm,
                            bottomMargin=10 * mm, title=f"Planejamento tributário {d.year} — {d.legal_name}",
                            author=d.office_name, creator="Planejamento Tributário", subject="Exercício " + str(d.year))
    doc.build(story_for(d))
    return buf.getvalue()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def report_data(row: dict) -> ReportData:
    """Linha de `db.get_report_data` → dados do PDF (somente campos determinísticos)."""
    approved = row["approved_at"]
    approver = row.get("approver") or {}
    return ReportData(
        recommendation_id=str(row["id"]), office_name=row["office_name"], legal_name=row["legal_name"],
        cnpj=row["cnpj"], year=int(row["year"]), rules_version=row["rules_version"], rules_hash=row["rules_hash"].strip(),
        decision_version=row["decision_version"], decision_hash=row["decision_hash"].strip(),
        snapshot_sha256=row["snapshot_sha256"].strip(), result_hash=(row["result_hash"] or "").strip(),
        threshold=Decimal(str(row["threshold"])), result=row["result"], sensitivity=row["sensitivity"],
        computed=row["computed"], assumptions=row["assumptions"],
        lines=[{"regime": l["regime"], "period": l["period"], "tax": l["tax"], "kind": l["kind"], "amount": l["amount"]}
               for l in row["lines"]],
        events=[{"event": e["event"], "comment": e["comment"]} for e in row["events"]],
        approver_name=approver.get("professional_name") or "—", approver_crc=approver.get("crc") or "—",
        approved_at=approved.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M") if approved else "—",
    )
