"""Orquestração dos jobs: extract, reconcile, export_xlsx; no ciclo 2, suggest_assumptions, calculate e
export_simulation; no ciclo 3, project e emit_report."""
import hashlib
import json
import sys
import time
from functools import lru_cache
from typing import Any

import psycopg

from worker import db
from worker.classify import classify
from worker.errors import (
    CnpjMismatch, HashMismatch, HasAdjustments, LayoutNotRecognized, NoTextLayer, NotPdf,
    Unclassified, WorkerError,
)
from worker.config import decision_params_path, load_settings
from worker.engine.assumptions import REFORM_GROUP, Assumptions, assumptions_hash, suggest
from worker.engine.calculate import NoCompleteCompetence, calculate
from worker.engine.decision import project
from worker.engine.decision_params import DecisionParams, load_decision_params
from worker.engine.projection import ProjectionError
from worker.report_pdf import build_recommendation_pdf, report_data, sha256
from worker.engine.memory import line_dict
from worker.engine.rules import RuleSet, RulesError, load_rules
from worker.engine.snapshot import SnapshotView
from worker.export_xlsx import build_simulation_xlsx, build_xlsx, export_path, simulation_export_path
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


@lru_cache(maxsize=1)
def default_rules() -> RuleSet:
    """Regras carregadas uma vez por processo; arquivo inválido levanta RulesError (o worker não sobe)."""
    settings = load_settings()
    return load_rules(settings.rules_dir, settings.rules_exercise)


@lru_cache(maxsize=1)
def default_decision_params() -> DecisionParams:
    return load_decision_params(load_settings().decision_params)


@lru_cache(maxsize=8)
def rules_for(year: int) -> RuleSet | None:
    """Regras de outro exercício (ex.: 2027, Reforma); None quando a pasta não existe."""
    settings = load_settings()
    try:
        return load_rules(settings.rules_dir, str(year))
    except RulesError:
        return None


@lru_cache(maxsize=8)
def decision_params_for(year: int) -> DecisionParams:
    return load_decision_params(decision_params_path(load_settings(), year))


REFORM_YEAR = 2027


def blocking(rows: list[dict], year: int) -> list[dict]:
    """Pendências que bloqueiam o exercício: o grupo da Reforma só conta no próprio exercício."""
    return [r for r in rows if r["status"] != "confirmed" and (r.get("grp") != REFORM_GROUP or year >= REFORM_YEAR)]


class Pipeline:
    def __init__(self, conn: psycopg.Connection, storage: Storage, rules: RuleSet | None = None,
                 decision: DecisionParams | None = None):
        self.conn = conn
        self.storage = storage
        self.rules = rules or default_rules()
        self.decision = decision or default_decision_params()

    def handle(self, job: dict[str, Any]) -> str | None:
        kind = job["kind"]
        if kind == "extract":
            return self.extract(job)
        if kind == "reconcile":
            return self.reconcile(job)
        if kind == "export_xlsx":
            return self.export(job)
        if kind == "suggest_assumptions":
            return self.suggest_assumptions(job)
        if kind == "calculate":
            return self.calculate(job)
        if kind == "export_simulation":
            return self.export_simulation(job)
        if kind == "project":
            return self.project(job)
        if kind == "emit_report":
            return self.emit_report(job)
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

    # ------------------------------------------------------------------ motor: premissas
    def suggest_assumptions(self, job: dict[str, Any]) -> str | None:
        office_id = job["office_id"]
        case_id = job["payload"]["case_id"]
        snap = db.get_case_snapshot(self.conn, case_id, office_id)
        if snap is None:
            return "dossiê não homologado"
        current = [r for r in db.load_assumptions(self.conn, case_id, office_id) if r["status"] == "confirmed"]
        rows = [s.as_row() for s in suggest(SnapshotView(snap["content"]), self.rules, Assumptions(current),
                                            rules_for(REFORM_YEAR))]
        db.upsert_suggestions(self.conn, case_id, office_id, rows)
        log("suggest.generated", job_id=job["id"], case_id=case_id, office_id=office_id, assumptions=len(rows),
            rules_version=self.rules.version)
        return None

    # ------------------------------------------------------------------ motor: cálculo
    def calculate(self, job: dict[str, Any]) -> str | None:
        office_id = job["office_id"]
        case_id = job["payload"]["case_id"]
        started = time.monotonic()
        snap = db.get_case_snapshot(self.conn, case_id, office_id)
        if snap is None:
            return "dossiê não homologado"
        rows = db.load_assumptions(self.conn, case_id, office_id)
        pending = blocking(rows, self.rules.exercise)
        if pending:   # premissa voltou a pendente depois do pedido (ex.: sugestões regeneradas)
            log("simulation.skipped", job_id=job["id"], case_id=case_id, pending=len(pending))
            return f"não calculado — {len(pending)} premissa(s) voltaram a pendente; confirme e peça o cálculo de novo"
        confirmed = [{"key": r["key"], "scope": r["scope"], "value": r["value"]} for r in rows
                     if r["status"] == "confirmed" or r["grp"] != REFORM_GROUP]
        a_hash = assumptions_hash(confirmed)
        # cópia gravada na simulação: a exportação usa esta, não as premissas atuais do dossiê
        used = [{"key": r["key"], "scope": r["scope"], "label": r["label"], "suggested_value": r["suggested_value"],
                 "value": r["value"], "justification": r["justification"],
                 "confirmed_at": r["confirmed_at"].isoformat() if r["confirmed_at"] else None} for r in rows]
        sha = snap["sha256"].strip()
        existing = db.find_simulation(self.conn, case_id, office_id, sha, a_hash, self.rules.hash)
        if existing is not None:
            log("simulation.reused", job_id=job["id"], case_id=case_id, simulation_id=existing["id"])
            return "resultado idêntico a uma simulação existente (mesmo snapshot, premissas e regras)"
        common = dict(case_id=case_id, office_id=office_id, snapshot_id=snap["id"], snapshot_sha=sha,
                      assumptions_hash=a_hash, rules_version=self.rules.version, rules_hash=self.rules.hash,
                      requested_by=job["payload"].get("requested_by"), assumptions=used)
        try:
            result = calculate(SnapshotView(snap["content"]), Assumptions(confirmed), self.rules)
        except NoCompleteCompetence as exc:
            db.save_simulation(self.conn, **common, status="failed", result={}, result_hash=None, lines=[],
                               error_code=exc.code, error_message=str(exc),
                               duration_ms=int((time.monotonic() - started) * 1000))
            log("simulation.failed", job_id=job["id"], case_id=case_id, code=exc.code)
            return exc.code
        duration = int((time.monotonic() - started) * 1000)
        sim_id = db.save_simulation(self.conn, **common, status="done", result=result.summary(),
                                    result_hash=result.result_hash, lines=[line_dict(l) for l in result.lines],
                                    duration_ms=duration)
        log("simulation.done", job_id=job["id"], case_id=case_id, office_id=office_id, simulation_id=sim_id,
            lines=len(result.lines), ranking=",".join(result.ranking), duration_ms=duration,
            not_calculated=",".join(r for r, v in result.regimes.items() if v.status != "calculado"))
        return None

    def export_simulation(self, job: dict[str, Any]) -> str | None:
        office_id = job["office_id"]
        sim = db.get_simulation(self.conn, job["payload"]["simulation_id"], office_id)
        if sim is None:
            return "simulação inexistente"
        lines = db.get_simulation_lines(self.conn, sim["id"], office_id)
        data = build_simulation_xlsx(sim, lines, sim["assumptions"])
        path = simulation_export_path(str(office_id), str(sim["case_id"]), str(sim["id"]))
        self.storage.upload(path, data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        log("simulation.exported", job_id=job["id"], simulation_id=sim["id"], office_id=office_id, bytes=len(data))
        return None

    # ------------------------------------------------------------------ ciclo 3: projeção e decisão
    def project(self, job: dict[str, Any]) -> str | None:
        office_id = job["office_id"]
        case_id = job["payload"]["case_id"]
        started = time.monotonic()
        snap = db.get_case_snapshot(self.conn, case_id, office_id)
        if snap is None:
            return "dossiê não homologado"
        year = int(job["payload"].get("year") or self.rules.exercise)
        rules = self.rules if year == self.rules.exercise else rules_for(year)
        if rules is None:
            return f"sem regras para o exercício {year}"
        decision = self.decision if year == self.rules.exercise else decision_params_for(year)
        rows = db.load_assumptions(self.conn, case_id, office_id)
        pending = blocking(rows, year)
        # prévia: premissas pendentes entram com o valor sugerido e bloqueiam a recomendação
        used = [{"key": r["key"], "scope": r["scope"], "label": r["label"],
                 "value": r["value"] if r["status"] == "confirmed" else r["suggested_value"],
                 "suggested_value": r["suggested_value"], "justification": r["justification"],
                 "status": r["status"], "confirmed_at": r["confirmed_at"].isoformat() if r["confirmed_at"] else None}
                for r in rows]
        blockers = [f"{len(pending)} premissa(s) pendente(s) de confirmação"] if pending else []
        a_hash = assumptions_hash([{"key": u["key"], "scope": u["scope"], "value": u["value"],
                                    "status": u["status"]} for u in used])
        threshold = db.load_decision_threshold(self.conn, office_id)
        sha = snap["sha256"].strip()
        existing = db.find_projection(self.conn, case_id, office_id, sha, a_hash, rules.hash,
                                      decision.hash, threshold)
        if existing is not None:
            log("projection.reused", job_id=job["id"], case_id=case_id, projection_id=existing["id"])
            return "resultado idêntico a uma projeção existente (mesmo snapshot, premissas, regras e política)"
        common = dict(case_id=case_id, office_id=office_id, snapshot_id=snap["id"], snapshot_sha=sha,
                      assumptions_hash=a_hash, rules_version=rules.version, rules_hash=rules.hash,
                      decision_version=decision.version, decision_hash=decision.hash, threshold=threshold,
                      assumptions=used, requested_by=job["payload"].get("requested_by"))
        view = SnapshotView(snap["content"])
        try:
            res = project(view, Assumptions(used), rules, decision, threshold, blockers, self.decision)
        except (ProjectionError, NoCompleteCompetence) as exc:
            code = getattr(exc, "code", "PROJECTION_BLOCKED")
            db.save_projection(self.conn, **common, year=0, status="failed", result={}, sensitivity=[],
                               recommendation={}, result_hash=None, lines=[], engine_runs=None,
                               duration_ms=int((time.monotonic() - started) * 1000), error_code=code,
                               error_message=str(exc))
            log("projection.failed", job_id=job["id"], case_id=case_id, code=code)
            return code
        rec = res.recommendation.as_dict()
        proj_id = db.save_projection(
            self.conn, **common, year=res.projected.year, status="done", result=res.summary(),
            sensitivity=[s.as_dict() for s in res.sensitivity], recommendation=rec, result_hash=res.result_hash,
            lines=res.lines(), engine_runs=res.runs, duration_ms=int((time.monotonic() - started) * 1000))
        log("projection.blocked" if rec["status"] == "bloqueado" else "projection.done", job_id=job["id"],
            case_id=case_id, office_id=office_id, projection_id=proj_id, status=rec["status"], regime=rec["regime"],
            engine_runs=res.runs, duration_ms=int((time.monotonic() - started) * 1000))
        return None

    def emit_report(self, job: dict[str, Any]) -> str | None:
        office_id = job["office_id"]
        rec_id = job["payload"]["recommendation_id"]
        row = db.get_report_data(self.conn, rec_id, office_id)
        if row is None:
            return "recomendação inexistente"
        if row["status"] != "aprovada":
            return "recomendação não está aprovada (status " + row["status"] + ")"
        data = build_recommendation_pdf(report_data(row))
        digest = sha256(data)
        path = db.report_path(str(office_id), str(row["case_id"]), str(rec_id))
        self.storage.upload(path, data, "application/pdf")
        if not db.mark_emitted(self.conn, rec_id, office_id, path, digest):
            return "recomendação alterada durante a emissão"
        log("report.emitted", job_id=job["id"], recommendation_id=rec_id, office_id=office_id, bytes=len(data))
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
