"""Abertura do PDF e reconstrução de linhas por coordenada.

Os relatórios Alterdata são "Print To PDF": a extração de texto linear embaralha colunas,
então as palavras são agrupadas pela posição vertical (`top`).
"""
from io import BytesIO

import pdfplumber

from worker.errors import NoTextLayer, NotPdf
from worker.models import Row, Word

LINE_TOL = 2.5  # pontos


def ensure_pdf(data: bytes) -> None:
    if not data.startswith(b"%PDF"):
        raise NotPdf("arquivo não é PDF")


def read_rows(data: bytes) -> tuple[list[Row], int]:
    """Retorna as linhas de todas as páginas e o número de páginas."""
    ensure_pdf(data)
    try:
        return _read_rows(data)
    except (NoTextLayer, NotPdf):
        raise
    except Exception as exc:  # PDF corrompido/malformado: rejeitar sem retry
        raise NotPdf("PDF inválido ou corrompido: " + type(exc).__name__) from exc


def _read_rows(data: bytes) -> tuple[list[Row], int]:
    rows: list[Row] = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        if not any((p.extract_text() or "").strip() for p in pdf.pages):
            raise NoTextLayer("PDF sem texto selecionável — OCR não suportado")
        for pno, page in enumerate(pdf.pages, start=1):
            words = sorted(
                page.extract_words(use_text_flow=False), key=lambda w: (w["top"], w["x0"])
            )
            current: list[Word] = []
            for w in words:
                word = Word(w["text"], w["x0"], w["x1"], w["top"], w["bottom"])
                if current and abs(word.top - current[0].top) > LINE_TOL:
                    rows.append(Row(pno, tuple(sorted(current, key=lambda x: x.x0))))
                    current = []
                current.append(word)
            if current:
                rows.append(Row(pno, tuple(sorted(current, key=lambda x: x.x0))))
        return rows, len(pdf.pages)
