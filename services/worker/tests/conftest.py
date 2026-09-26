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
    "folha_202608": "2.Resumo da Folha 08.pdf",
    "dre_202608": "3.DRE 08.pdf",
    "balancete_202608": "4.Balancete 08.pdf",
}
# folha, DRE e balancete de 06 e 07: com eles as três competências ficam completas (golden motor_202606_08)
EXTRA_SAMPLE_FILES = {
    "folha_202606": "2.Resumo da Folha 06.pdf",
    "folha_202607": "2.Resumo da Folha 07.pdf",
    "dre_202606": "3.DRE 06.pdf",
    "dre_202607": "3.DRE 07.pdf",
    "balancete_202606": "4.Balancete 06.pdf",
    "balancete_202607": "4.Balancete 07.pdf",
    "livro_202608": "Livro Apuração ICMS 08.pdf",       # opcional (ciclo 4): Registro de Apuração do ICMS
}
ALL_SAMPLE_FILES = {**SAMPLE_FILES, **EXTRA_SAMPLE_FILES}
SAMPLE_CNPJ = "37704456000142"

DEFAULT_MAPPINGS = {
    ("vendas", "BALANCETE_ALTERDATA"): "40101",
    ("vendas", "DRE_ALTERDATA"): "4.1.1.01.001",
    ("simples_despesa", "BALANCETE_ALTERDATA"): "34009",
    ("simples_despesa", "DRE_ALTERDATA"): "3.1.1.15.009",
    ("simples_a_recolher", "BALANCETE_ALTERDATA"): "20308",
    ("inss_a_pagar", "BALANCETE_ALTERDATA"): "20403",
    ("compras_mercadorias", "BALANCETE_ALTERDATA"): "13101",
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
    missing = [n for n in ALL_SAMPLE_FILES.values() if not (base / n).is_file()]
    if missing:
        skip_or_fail("amostras ausentes em " + str(base) + " (defina SAMPLES_DIR)")

    def load(name: str) -> bytes:
        return (base / ALL_SAMPLE_FILES[name]).read_bytes()

    return load


def build_snapshot_content(load, names=None) -> dict:
    """Conteúdo de snapshot no mesmo formato de `homologate_case`, a partir das amostras (sem banco)."""
    from worker.pipeline import parse_document

    files, values, validations = [], [], []
    for name in names or SAMPLE_FILES:
        result, checks = parse_document(load(name))
        file_id = "file-" + name
        files.append({"id": file_id, "original_name": ALL_SAMPLE_FILES[name], "doc_type": result.doc_type.value,
                      "competence": result.competence + "-01", "parser_version": result.parser_version})
        for v in result.values:
            values.append({
                "id": f"{file_id}-{v.ordinal}", "file_id": file_id, "ordinal": v.ordinal,
                "doc_type": result.doc_type.value, "competence": v.competence + "-01", "section": v.section,
                "field_key": v.field_key, "label": v.label, "account_code": v.account_code, "column": v.column,
                "value": v.value, "original_value": v.value, "adjusted": False, "nature": v.nature,
                "page": v.page, "bbox": list(v.bbox),
            })
        validations += [{"file_id": file_id, "rule": c.rule, "status": c.status} for c in checks]
    return {"schema_version": 1, "company": {"cnpj": SAMPLE_CNPJ}, "files": files, "values": values,
            "validations": validations, "reconciliations": []}


def accepted_assumptions(view, rules, overrides: dict | None = None, extra_months: tuple = ()):
    """Premissas sugeridas aceitas como estão (+ sobrescritas por (key, scope)).

    `extra_months` inclui perfis de atividade de competências que não são completas (para recalcular o
    Simples de meses só com PGDAS-D)."""
    from worker.engine.activities import declared_zero_taxes, match_profile
    from worker.engine.assumptions import Assumptions, confirm_all_suggested, suggest

    rows = confirm_all_suggested(suggest(view, rules))
    for comp in extra_months:
        for act in view.activities(comp):
            profile, _ = match_profile(act.description, rules)
            rows.append({"key": "atividade.perfil", "scope": "atividade:" + act.key, "value": profile.as_value()})
            rows.append({"key": "atividade.tributos_zerados", "scope": "atividade:" + act.key,
                         "value": declared_zero_taxes(act, rules)})
    by_key = {(r["key"], r["scope"]): r for r in rows}
    for (key, scope), value in (overrides or {}).items():
        by_key[(key, scope)] = {"key": key, "scope": scope, "value": value}
    return Assumptions(list(by_key.values()))


@pytest.fixture(scope="session")
def snapshot_content(sample):
    return build_snapshot_content(sample)


@pytest.fixture(scope="session")
def snapshot_content_06_08(sample):
    """Os 12 documentos: 06, 07 e 08/2026 completos."""
    return build_snapshot_content(sample, ALL_SAMPLE_FILES)


@pytest.fixture(scope="session")
def rules():
    from worker.config import load_settings
    from worker.engine.rules import load_rules

    return load_rules(load_settings().rules_dir, "2026")


@pytest.fixture(scope="session")
def decision_params():
    from worker.config import load_settings
    from worker.engine.decision_params import load_decision_params

    return load_decision_params(load_settings().decision_params)


def golden_assumptions_06_08(view, rules, golden, overrides: dict | None = None):
    """Premissas sugeridas aceitas + declarações do golden (as mesmas do caso dourado do ciclo 2)."""
    g = golden("motor_202606_08")
    base = {(k, "caso"): v for k, v in g["assumption_overrides"].items()}
    return accepted_assumptions(view, rules, {**base, **(overrides or {})})


@pytest.fixture(scope="session")
def rules_2027():
    from worker.config import load_settings
    from worker.engine.rules import load_rules

    return load_rules(load_settings().rules_dir, "2027")


@pytest.fixture(scope="session")
def decision_params_2027():
    from worker.config import decision_params_path, load_settings
    from worker.engine.decision_params import load_decision_params

    return load_decision_params(decision_params_path(load_settings(), 2027))


REFORM_GOLDEN = {"reforma.cbs_aliquota": "0.095", "reforma.ibs_aliquota": "0.001", "reforma.crescimento": "0.05"}


def reform_assumptions(view, rules, rules_2027, golden, reform_values: dict | None = REFORM_GOLDEN):
    """Premissas do caso dourado (ciclo 2) + premissas de 2027 (sugestões aceitas; alíquotas/crescimento dados)."""
    from worker.engine.assumptions import Assumptions, suggest

    g = golden("motor_202606_08")
    values = {**g["assumption_overrides"], **(reform_values or {})}
    rows = [{"key": x.key, "scope": x.scope, "value": values.get(x.key, x.suggested_value)}
            for x in suggest(view, rules, None, rules_2027)]
    return Assumptions(rows)


@pytest.fixture(scope="session")
def golden():
    def load(name: str) -> dict:
        return json.loads((GOLDEN / (name + ".json")).read_text(encoding="utf-8"))

    return load


# ---------------------------------------------------------------- banco local
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
CLEANUP_TABLES = [
    "recommendation_events", "recommendations", "projection_lines", "projections",
    "simulation_lines", "simulations", "assumptions",
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
