"""Gera o XLSX do dossiê homologado a partir do snapshot (AT-021)."""
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

MONEY_FORMAT = "#,##0.00"

SHEETS = {
    "Valores": [
        ("file_id", "Arquivo"), ("ordinal", "Ordem"), ("doc_type", "Documento"), ("competence", "Competência"),
        ("section", "Seção"), ("field_key", "Campo"), ("label", "Rótulo"), ("account_code", "Conta/rubrica"),
        ("column", "Coluna"), ("value", "Valor efetivo"), ("original_value", "Valor original"),
        ("adjusted", "Ajustado"), ("nature", "D/C"), ("page", "Página"), ("bbox", "Posição (bbox)"),
    ],
    "Ajustes": [
        ("value_id", "Valor"), ("old_value", "Valor anterior"), ("new_value", "Novo valor"),
        ("reason", "Motivo"), ("author", "Autor"), ("created_at", "Data/hora"),
    ],
    "Validações": [
        ("file_id", "Arquivo"), ("rule", "Regra"), ("status", "Status"), ("expected", "Esperado"),
        ("actual", "Encontrado"), ("diff", "Diferença"), ("detail", "Detalhe"),
    ],
    "Conciliações": [
        ("competence", "Competência"), ("rule", "Regra"), ("description", "Descrição"),
        ("left_label", "Fonte A"), ("left_value", "Valor A"), ("right_label", "Fonte B"),
        ("right_value", "Valor B"), ("diff", "Diferença"), ("tolerance", "Tolerância"),
        ("status", "Status"), ("justification", "Justificativa"), ("justified_by", "Justificado por"),
        ("justified_at", "Justificado em"),
    ],
}
SOURCE_KEY = {"Valores": "values", "Ajustes": "adjustments", "Validações": "validations",
              "Conciliações": "reconciliations"}


def _cell(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, dict)):
        return str(value)
    return value


def build_xlsx(content: dict[str, Any], sha256: str) -> bytes:
    wb = Workbook()
    resumo = wb.active
    resumo.title = "Resumo"
    case = content.get("case", {})
    company = content.get("company", {})
    for row in [
        ("Hash do snapshot (SHA-256)", sha256),
        ("Empresa", company.get("legal_name")),
        ("CNPJ", company.get("cnpj")),
        ("Período", str(case.get("period_start")) + " a " + str(case.get("period_end"))),
        ("Tolerância de conciliação (R$)", _cell(content.get("tolerance_brl"))),
        ("Homologado em", content.get("homologated_at")),
        ("Homologado por", content.get("homologated_by")),
        ("Arquivos", len(content.get("files", []))),
        ("Valores", len(content.get("values", []))),
    ]:
        resumo.append(row)
    resumo.column_dimensions["A"].width = 34
    resumo.column_dimensions["B"].width = 70

    for title, columns in SHEETS.items():
        ws = wb.create_sheet(title)
        ws.append([label for _, label in columns])
        for c in ws[1]:
            c.font = Font(bold=True)
        for item in content.get(SOURCE_KEY[title], []):
            ws.append([_cell(item.get(key)) for key, _ in columns])
        for idx, (key, _) in enumerate(columns, start=1):
            if key in ("value", "original_value", "old_value", "new_value", "expected", "actual", "diff",
                       "left_value", "right_value", "tolerance"):
                for (cell,) in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                    cell.number_format = MONEY_FORMAT
        ws.freeze_panes = "A2"

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_path(office_id: str, case_id: str, snapshot_id: str) -> str:
    return f"{office_id}/{case_id}/exports/{snapshot_id}.xlsx"
