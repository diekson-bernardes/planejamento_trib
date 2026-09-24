"""Fixtures compartilhadas: amostras reais (fora do Git), golden e banco local."""
import hashlib
import json
import os
import uuid
from pathlib import Path

import psycopg
import pytest

REPO = Path(__file__).resolve().parents[3]
GOLDEN = Path(__file__).resolve().parent / "golden"

SAMPLE_FILES = {
    "pgdas_202606": "1.PGDASD-DECLARACAO-37704456202606001.pdf",
    "pgdas_202607": "1.PGDASD-DECLARACAO-37704456202607001.pdf",
    "pgdas_202608": "1.PGDASD-DECLARACAO-37704456202608001.pdf",
    "folha_202608": "2.Resumo da Folha.pdf",
    "dre_202608": "3.DRE.pdf",
    "balancete_202608": "Balancete.pdf",
}
SAMPLE_CNPJ = "37704456000142"

DEFAULT_MAPPINGS = {
    ("vendas", "BALANCETE_ALTERDATA"): "40101",
    ("vendas", "DRE_ALTERDATA"): "4.1.1.01.001",
    ("simples_despesa", "BALANCETE_ALTERDATA"): "34009",
    ("simples_despesa", "DRE_ALTERDATA"): "3.1.1.15.009",
    ("simples_a_recolher", "BALANCETE_ALTERDATA"): "20308",
    ("inss_a_pagar", "BALANCETE_ALTERDATA"): "20403",
    ("fgts_a_pagar", "BALANCETE_ALTERDATA"): "20405",
    ("salarios_a_pagar", "BALANCETE_ALTERDATA"): "20401",
}


STRICT = os.environ.get("VERIFY_STRICT") == "1"  # no Verify Gate, pré-requisito ausente é falha


def skip_or_fail(reason: str):
    if STRICT:
        pytest.fail(reason + " — obrigatório no npm run verify", pytrace=False)
    pytest.skip(reason)


def samples_dir() -> Path:
    raw = os.environ.get("SAMPLES_DIR", "docs/Amostras")
    path = Path(raw)
    return path if path.is_absolute() else REPO / path


@pytest.fixture(scope="session")
def sample():
    base = samples_dir()
    missing = [n for n in SAMPLE_FILES.values() if not (base / n).is_file()]
    if missing:
        skip_or_fail("amostras ausentes em " + str(base) + " (defina SAMPLES_DIR)")

    def load(name: str) -> bytes:
        return (base / SAMPLE_FILES[name]).read_bytes()

    return load


@pytest.fixture(scope="session")
def golden():
    def load(name: str) -> dict:
        return json.loads((GOLDEN / (name + ".json")).read_text(encoding="utf-8"))

    return load


# ---------------------------------------------------------------- banco local
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
CLEANUP_TABLES = [
    "audit_events", "snapshots", "reconciliations", "validations", "value_adjustments",
    "extracted_values", "jobs", "source_files", "tax_cases", "account_mappings", "companies",
    "office_members", "offices",
]


@pytest.fixture
def db_conn():
    from worker import db

    try:
        conn = db.connect(DATABASE_URL)
    except psycopg.OperationalError:
        skip_or_fail("Postgres local indisponível (npm run db:start)")
    yield conn
    conn.close()


class MemoryStorage:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def download(self, path: str) -> bytes:
        from worker.errors import FileNotFound

        if path not in self.objects:
            raise FileNotFound("objeto não encontrado")
        return self.objects[path]

    def upload(self, path: str, data: bytes, content_type: str) -> None:
        self.objects[path] = data


class TenantFixture:
    """Cria um escritório/empresa/dossiê isolado para o teste e remove tudo no fim."""

    def __init__(self, conn, cnpj: str = SAMPLE_CNPJ):
        self.conn = conn
        self.office_id = uuid.uuid4()
        self.company_id = uuid.uuid4()
        self.case_id = uuid.uuid4()
        self.user_id = "a2222222-2222-4222-8222-222222222222"  # analista do seed (FK de uploaded_by)
        self.storage = MemoryStorage()
        with conn.transaction():
            conn.execute("insert into offices (id, name) values (%s, 'Teste worker')", (self.office_id,))
            conn.execute("insert into companies (id, office_id, cnpj, legal_name) values (%s, %s, %s, 'Empresa teste')",
                         (self.company_id, self.office_id, cnpj))
            conn.execute("insert into tax_cases (id, office_id, company_id, period_start, period_end) "
                         "values (%s, %s, %s, '2026-06-01', '2026-08-31')",
                         (self.case_id, self.office_id, self.company_id))
            for (target, doc_type), code in DEFAULT_MAPPINGS.items():
                conn.execute("insert into account_mappings (office_id, target, doc_type, account_code) "
                             "values (%s, %s, %s, %s)", (self.office_id, target, doc_type, code))

    def add_file(self, data: bytes, name: str = "doc.pdf"):
        file_id = uuid.uuid4()
        path = f"{self.office_id}/{self.case_id}/{file_id}.pdf"
        self.storage.objects[path] = data
        with self.conn.transaction():
            self.conn.execute(
                "insert into source_files (id, office_id, case_id, storage_path, original_name, sha256, size_bytes, uploaded_by) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s)",
                (file_id, self.office_id, self.case_id, path, name, hashlib.sha256(data).hexdigest(), len(data), self.user_id),
            )
        return file_id

    def cleanup(self):
        with self.conn.transaction():
            self.conn.execute("set local session_replication_role = replica")
            for table in CLEANUP_TABLES:
                col = "id" if table == "offices" else "office_id"
                self.conn.execute(f"delete from {table} where {col} = %s", (self.office_id,))


@pytest.fixture
def tenant(db_conn):
    t = TenantFixture(db_conn)
    yield t
    t.cleanup()


def minimal_pdf(text: str | None = None) -> bytes:
    """PDF de 1 página, com ou sem texto, montado à mão (para testes de rejeição)."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"]
    if text is None:
        objects.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] >>")
    else:
        stream = f"BT /F1 12 Tf 20 150 Td ({text}) Tj ET"
        objects.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Contents 4 0 R "
                       "/Resources << /Font << /F1 5 0 R >> >> >>")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out
