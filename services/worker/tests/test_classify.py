"""AT-001, AT-010, AT-013: classificação, PDF sem texto e documento não reconhecido."""
import pytest

from conftest import SAMPLE_CNPJ, minimal_pdf
from worker.classify import classify
from worker.errors import NoTextLayer, NotPdf, Unclassified
from worker.models import DocType
from worker.pdf.layout import read_rows

EXPECTED = {
    "pgdas_202606": (DocType.PGDAS_D, "2026-06"),
    "pgdas_202607": (DocType.PGDAS_D, "2026-07"),
    "pgdas_202608": (DocType.PGDAS_D, "2026-08"),
    "folha_202608": (DocType.FOLHA_ALTERDATA, "2026-08"),
    "dre_202608": (DocType.DRE_ALTERDATA, "2026-08"),
    "balancete_202608": (DocType.BALANCETE_ALTERDATA, "2026-08"),
    "livro_202608": (DocType.LIVRO_ICMS_ALTERDATA, "2026-08"),
}


@pytest.mark.samples
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_samples_are_classified(sample, name):
    rows, _ = read_rows(sample(name))
    cls = classify(rows)
    assert (cls.doc_type, cls.competence) == EXPECTED[name]
    assert cls.cnpj == SAMPLE_CNPJ
    assert cls.monthly


def test_pdf_without_text_layer_is_rejected():
    with pytest.raises(NoTextLayer) as exc:
        read_rows(minimal_pdf(None))
    assert exc.value.code == "NO_TEXT"
    assert "OCR não suportado" in str(exc.value)


def test_non_pdf_is_rejected():
    with pytest.raises(NotPdf):
        read_rows(b"PK\x03\x04 planilha")


def test_unknown_document_is_unclassified():
    rows, _ = read_rows(minimal_pdf("Documento qualquer sem cabecalho conhecido"))
    with pytest.raises(Unclassified):
        classify(rows)


def test_forced_type_skips_detection():
    rows, _ = read_rows(minimal_pdf("Documento qualquer"))
    assert classify(rows, DocType.DRE_ALTERDATA).doc_type == DocType.DRE_ALTERDATA
