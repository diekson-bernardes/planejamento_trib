"""Orquestração dos jobs: extract, reconcile e export_xlsx."""
import hashlib
import json
import sys
import time
from typing import Any

import psycopg

from worker import db
from worker.classify import classify
from worker.errors import (
    CnpjMismatch, HashMismatch, HasAdjustments, LayoutNotRecognized, NoTextLayer, NotPdf,
    Unclassified, WorkerError,
)
from worker.export_xlsx import build_xlsx, export_path
from worker.models import DocType, ParseResult
from worker.parsers import get_parser
from worker.pdf.layout import read_rows
from worker.reconcile import Facts, reconcile
from worker.storage import Storage
from worker.validations import validate

# Erro de domínio → status do arquivo. Nenhum deles é repetido.
FILE_STATUS = {
    NotPdf: "rejected",
    NoTextLayer: "rejected",
    HashMismatch: "rejected",
    Unclassified: "unclassified",
    CnpjMismatch: "cnpj_mismatch",
}


def log(event: str, **fields: Any) -> None:
    """Log estruturado em JSON, somente com IDs e códigos (nunca texto do PDF)."""
    record = {"event": event, "ts": round(time.time(), 3), **{k: str(v) if v is not None else None for k, v in fields.items()}}
    sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def result_hash(result: ParseResult) -> str:
    payload = {
        "doc_type": result.doc_type.value,
        "parser_version": result.parser_version,
        "values": [v.model_dump(mode="json") for v in result.values],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_document(data: bytes, forced: DocType | None = None):
    """PDF → (ParseResult, validações). Sem banco: usado pelo pipeline e pelos testes."""
    rows, pages = read_rows(data)
    cls = classify(rows, forced)
    result = get_parser(cls.doc_type).parse(rows, pages)
    return result, validate(result, cls.monthly)


class Pipeline:
    def __init__(self, conn: psycopg.Connection, storage: Storage):
        self.conn = conn
        self.storage = storage

    def handle(self, job: dict[str, Any]) -> str | None:
        kind = job["kind"]
        if kind == "extract":
            return self.extract(job)
        if kind == "reconcile":
            return self.reconcile(job)
        if kind == "export_xlsx":
            return self.export(job)
        raise ValueError("tipo de job desconhecido: " + kind)

    # ------------------------------------------------------------------ extract
    def extract(self, job: dict[str, Any]) -> str | None:
        office_id = job["office_id"]
        payload = job["payload"]
        file = db.get_file(self.conn, payload["file_id"], office_id)
        if file is None:
            return "arquivo removido"
        case = db.get_case(self.conn, file["case_id"], office_id)
        if case is None or case["status"] == "homologated":
            return "dossiê homologado ou inexistente"
        if db.file_has_adjustments(self.conn, file["id"], office_id):
            # Valores e ajustes continuam válidos: não altera o status do arquivo.
            log("file.reprocess_skipped", job_id=job["id"], file_id=file["id"], office_id=office_id,
                code=HasAdjustments.code)
            return HasAdjustments.code
        started = time.monotonic()
        db.set_file_status(self.conn, file["id"], office_id, "processing")
        try:
            data = self.storage.download(file["storage_path"])
            if hashlib.sha256(data).hexdigest() != file["sha256"].strip():
                raise HashMismatch("hash do arquivo não confere com o registrado no upload")
            forced = DocType(payload["manual_doc_type"]) if payload.get("manual_doc_type") else None
            result, validations = parse_document(data, forced)
            if result.cnpj != case["company_cnpj"].strip():
                db.set_file_status(self.conn, file["id"], office_id, "cnpj_mismatch", doc_type=result.doc_type.value,
                                   cnpj=result.cnpj, competence=db.month_start(result.competence),
                                   error_code=CnpjMismatch.code,
                                   error_message="CNPJ do documento diferente do CNPJ da empresa do dossiê")
                log("file.cnpj_mismatch", job_id=job["id"], file_id=file["id"], office_id=office_id)
                return CnpjMismatch.code
            digest = result_hash(result)
            db.save_extraction(self.conn, file, result, validations, digest)
            log("file.extracted", job_id=job["id"], file_id=file["id"], office_id=office_id,
                doc_type=result.doc_type.value, parser_version=result.parser_version,
                values=len(result.values), failed_validations=sum(v.status == "fail" for v in validations),
                duration_ms=int((time.monotonic() - started) * 1000))
            return None
        except WorkerError as exc:
            if exc.retryable:
                db.set_file_status(self.conn, file["id"], office_id, "uploaded")
                raise
            status = FILE_STATUS.get(type(exc), "failed")
            parser_version = None
            if isinstance(exc, LayoutNotRecognized):
                parser_version = str(exc).rsplit("parser ", 1)[-1].rstrip(")") if "parser " in str(exc) else None
            db.set_file_status(self.conn, file["id"], office_id, status, error_code=exc.code,
                               error_message=str(exc), parser_version=parser_version)
            log("file." + status, job_id=job["id"], file_id=file["id"], office_id=office_id, code=exc.code)
            return exc.code
        finally:
            db.refresh_case_status(self.conn, file["case_id"], office_id)

    # ------------------------------------------------------------------ reconcile
    def reconcile(self, job: dict[str, Any]) -> str | None:
        office_id = job["office_id"]
        case = db.get_case(self.conn, job["payload"]["case_id"], office_id)
        if case is None or case["status"] == "homologated":
            return "dossiê homologado ou inexistente"
        facts = Facts(db.load_facts(self.conn, case["id"], office_id))
        mappings = db.load_mappings(self.conn, office_id, case["company_id"])
        tolerance = db.load_tolerance(self.conn, office_id)
        results = reconcile(facts, mappings, tolerance)
        db.save_reconciliations(self.conn, case["id"], office_id, results)
        log("case.reconciled", job_id=job["id"], case_id=case["id"], office_id=office_id,
            divergent=sum(r.status == "divergent" for r in results),
            missing_source=sum(r.status == "missing_source" for r in results))
        return None

    # ------------------------------------------------------------------ export
    def export(self, job: dict[str, Any]) -> str | None:
        office_id = job["office_id"]
        snap = db.get_snapshot(self.conn, job["payload"]["snapshot_id"], office_id)
        if snap is None:
            return "snapshot inexistente"
        data = build_xlsx(snap["content"], snap["sha256"].strip())
        path = export_path(str(office_id), str(snap["case_id"]), str(snap["id"]))
        self.storage.upload(path, data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        log("export.generated", job_id=job["id"], case_id=snap["case_id"], office_id=office_id, bytes=len(data))
        return None

    # ------------------------------------------------------------------ loop
    def run_once(self, lease_seconds: int, max_attempts: int) -> bool:
        """Processa um job. Devolve False quando a fila está vazia."""
        job = db.claim_job(self.conn, lease_seconds)
        if job is None:
            return False
        try:
            note = self.handle(job)
            db.finish_job(self.conn, job["id"], job["office_id"], note)
        except Exception as exc:  # falha transitória ou inesperada: retry com backoff
            if self.conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                self.conn.rollback()
            code = exc.code if isinstance(exc, WorkerError) else "INTERNAL"
            retried = db.retry_or_fail_job(self.conn, job["id"], job["office_id"], job["attempts"],
                                           max_attempts, code + ": " + type(exc).__name__)
            log("job.retry" if retried else "job.failed", job_id=job["id"], kind=job["kind"],
                office_id=job["office_id"], attempts=job["attempts"], code=code)
            if not retried and job["kind"] == "extract":
                db.set_file_status(self.conn, job["payload"]["file_id"], job["office_id"], "failed",
                                   error_code=code, error_message="falha após " + str(job["attempts"]) + " tentativas")
                db.refresh_case_status(self.conn, job["payload"]["case_id"], job["office_id"])
        return True

    def drain(self, lease_seconds: int = 300, max_attempts: int = 3, limit: int = 1000) -> int:
        """Processa até a fila esvaziar (usado em testes e no smoke)."""
        count = 0
        while count < limit and self.run_once(lease_seconds, max_attempts):
            count += 1
        return count
