"""Acesso ao Postgres pelo worker.

A conexão do worker ignora RLS (role de serviço): TODA consulta e escrita filtra ou grava
`office_id` explicitamente, vindo do job.
"""
import json
from datetime import date
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb, set_json_loads

from worker.models import DocType, ParseResult, ReconciliationResult, ValidationResult
from worker.reconcile import Fact

set_json_loads(lambda s: json.loads(s, parse_float=Decimal))


def connect(database_url: str) -> psycopg.Connection:
    # autocommit: leituras avulsas não deixam transação aberta; escritas usam conn.transaction().
    return psycopg.connect(database_url, row_factory=dict_row, autocommit=True)


def month_start(comp: str) -> date:
    return date(int(comp[:4]), int(comp[5:7]), 1)


# ---------------------------------------------------------------- jobs
CLAIM_SQL = """
update jobs set status = 'running', attempts = attempts + 1, locked_at = now()
where id = (
  select id from jobs
  where (status = 'queued' and run_after <= now())
     or (status = 'running' and locked_at < now() - make_interval(secs => %(lease)s))
  order by created_at
  for update skip locked
  limit 1
)
returning id, office_id, kind, payload, attempts
"""


def claim_job(conn: psycopg.Connection, lease_seconds: int) -> dict[str, Any] | None:
    with conn.transaction():
        return conn.execute(CLAIM_SQL, {"lease": lease_seconds}).fetchone()


def finish_job(conn: psycopg.Connection, job_id, office_id, note: str | None = None) -> None:
    with conn.transaction():
        conn.execute(
            "update jobs set status = 'done', finished_at = now(), last_error = %s, locked_at = null "
            "where id = %s and office_id = %s",
            (note, job_id, office_id),
        )


def retry_or_fail_job(conn: psycopg.Connection, job_id, office_id, attempts: int, max_attempts: int,
                      error: str) -> bool:
    """Devolve True se o job voltou para a fila."""
    retry = attempts < max_attempts
    with conn.transaction():
        if retry:
            conn.execute(
                "update jobs set status = 'queued', locked_at = null, last_error = %s, "
                "run_after = now() + make_interval(secs => %s) where id = %s and office_id = %s",
                (error, 2 ** attempts, job_id, office_id),
            )
        else:
            conn.execute(
                "update jobs set status = 'failed', locked_at = null, last_error = %s, finished_at = now() "
                "where id = %s and office_id = %s",
                (error, job_id, office_id),
            )
    return retry


# ---------------------------------------------------------------- arquivos e dossiês
def get_file(conn: psycopg.Connection, file_id, office_id) -> dict[str, Any] | None:
    return conn.execute(
        "select * from source_files where id = %s and office_id = %s", (file_id, office_id)
    ).fetchone()


def get_case(conn: psycopg.Connection, case_id, office_id) -> dict[str, Any] | None:
    return conn.execute(
        "select c.*, co.cnpj as company_cnpj from tax_cases c "
        "join companies co on co.id = c.company_id and co.office_id = c.office_id "
        "where c.id = %s and c.office_id = %s",
        (case_id, office_id),
    ).fetchone()


def set_file_status(conn: psycopg.Connection, file_id, office_id, status: str, **fields: Any) -> None:
    cols = {"status": status, **fields}
    assignments = ", ".join(f"{k} = %({k})s" for k in cols)
    with conn.transaction():
        conn.execute(
            f"update source_files set {assignments}, updated_at = now() "
            "where id = %(__id)s and office_id = %(__office)s",
            {**cols, "__id": file_id, "__office": office_id},
        )


def file_has_adjustments(conn: psycopg.Connection, file_id, office_id) -> bool:
    row = conn.execute(
        "select exists (select 1 from value_adjustments a join extracted_values v on v.id = a.value_id "
        "where v.file_id = %s and v.office_id = %s) as has",
        (file_id, office_id),
    ).fetchone()
    return bool(row["has"])


def save_extraction(conn: psycopg.Connection, file: dict[str, Any], result: ParseResult,
                    validations: list[ValidationResult], result_hash: str) -> None:
    """Substitui atomicamente os valores e validações do arquivo (idempotente)."""
    office_id, case_id, file_id = file["office_id"], file["case_id"], file["id"]
    competence = month_start(result.competence)
    with conn.transaction():
        conn.execute("delete from extracted_values where file_id = %s and office_id = %s", (file_id, office_id))
        conn.execute("delete from validations where file_id = %s and office_id = %s", (file_id, office_id))
        with conn.cursor() as cur:
            cur.executemany(
                "insert into extracted_values (office_id, case_id, file_id, ordinal, doc_type, competence, "
                "section, field_key, label, account_code, column_name, value, nature, page, bbox, parser_version) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    (office_id, case_id, file_id, v.ordinal, result.doc_type.value, month_start(v.competence),
                     v.section, v.field_key, v.label, v.account_code, v.column, v.value, v.nature, v.page,
                     [Decimal(str(x)) for x in v.bbox], result.parser_version)
                    for v in result.values
                ],
            )
            cur.executemany(
                "insert into validations (office_id, case_id, file_id, rule, status, expected, actual, diff, detail) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [(office_id, case_id, file_id, r.rule, r.status, r.expected, r.actual, r.diff, r.detail)
                 for r in validations],
            )
        conn.execute(
            "update source_files set status = 'extracted', doc_type = %s, cnpj = %s, competence = %s, "
            "parser_version = %s, result_hash = %s, pages = %s, error_code = null, error_message = null, "
            "updated_at = now() where id = %s and office_id = %s",
            (result.doc_type.value, result.cnpj, competence, result.parser_version, result_hash,
             result.pages, file_id, office_id),
        )
        enqueue(conn, office_id, "reconcile", {"case_id": str(case_id)},
                f"reconcile:{case_id}:file:{file_id}:{result_hash}")


def enqueue(conn: psycopg.Connection, office_id, kind: str, payload: dict, key: str) -> None:
    conn.execute(
        "insert into jobs (office_id, kind, payload, idempotency_key) values (%s, %s, %s, %s) "
        "on conflict (idempotency_key) do nothing",
        (office_id, kind, Jsonb(payload), key),
    )


def refresh_case_status(conn: psycopg.Connection, case_id, office_id) -> None:
    """processing → review quando nenhum arquivo aguarda processamento."""
    with conn.transaction():
        conn.execute(
            "update tax_cases set status = 'review' where id = %(c)s and office_id = %(o)s "
            "and status = 'processing' and not exists (select 1 from source_files "
            "where case_id = %(c)s and office_id = %(o)s and status in ('uploaded', 'processing'))",
            {"c": case_id, "o": office_id},
        )


# ---------------------------------------------------------------- conciliação
def load_facts(conn: psycopg.Connection, case_id, office_id) -> list[Fact]:
    rows = conn.execute(
        "select ev.doc_type, to_char(ev.competence, 'YYYY-MM') as competence, ev.field_key, "
        "ev.column_name, ev.section, ev.effective_value, ev.nature "
        "from effective_values ev join source_files f on f.id = ev.file_id and f.office_id = ev.office_id "
        "where ev.case_id = %s and ev.office_id = %s and f.status = 'extracted' "
        "order by ev.file_id, ev.ordinal",
        (case_id, office_id),
    ).fetchall()
    return [Fact(DocType(r["doc_type"]), r["competence"], r["field_key"], r["column_name"], r["section"],
                 r["effective_value"], r["nature"]) for r in rows]


def load_mappings(conn: psycopg.Connection, office_id, company_id) -> dict[tuple[str, str], str]:
    rows = conn.execute(
        "select target, doc_type, account_code, company_id from account_mappings "
        "where office_id = %s and (company_id is null or company_id = %s) "
        "order by (company_id is null) desc",
        (office_id, company_id),
    ).fetchall()
    # Padrão do escritório primeiro; mapeamento da empresa sobrescreve.
    return {(r["target"], r["doc_type"]): r["account_code"] for r in rows}


def load_tolerance(conn: psycopg.Connection, office_id) -> Decimal:
    row = conn.execute("select settings ->> 'tolerance_brl' as t from offices where id = %s", (office_id,)).fetchone()
    return Decimal(row["t"]) if row and row["t"] is not None else Decimal("1.00")


def save_reconciliations(conn: psycopg.Connection, case_id, office_id, results: list[ReconciliationResult]) -> None:
    with conn.transaction():
        keep = []
        for r in results:
            comp = month_start(r.competence)
            keep.append((comp, r.rule))
            conn.execute(
                """
                insert into reconciliations (office_id, case_id, competence, rule, description, left_label,
                  left_value, right_label, right_value, diff, tolerance, status, details, updated_at)
                values (%(o)s, %(c)s, %(comp)s, %(rule)s, %(desc)s, %(ll)s, %(lv)s, %(rl)s, %(rv)s, %(diff)s,
                  %(tol)s, %(status)s, %(details)s, now())
                on conflict (case_id, competence, rule) do update set
                  description = excluded.description, left_label = excluded.left_label,
                  left_value = excluded.left_value, right_label = excluded.right_label,
                  right_value = excluded.right_value, diff = excluded.diff, tolerance = excluded.tolerance,
                  status = excluded.status, details = excluded.details, updated_at = now(),
                  -- justificativa só sobrevive se os valores comparados não mudaram
                  justification = case when reconciliations.left_value is not distinct from excluded.left_value
                    and reconciliations.right_value is not distinct from excluded.right_value
                    then reconciliations.justification end,
                  justified_by = case when reconciliations.left_value is not distinct from excluded.left_value
                    and reconciliations.right_value is not distinct from excluded.right_value
                    then reconciliations.justified_by end,
                  justified_at = case when reconciliations.left_value is not distinct from excluded.left_value
                    and reconciliations.right_value is not distinct from excluded.right_value
                    then reconciliations.justified_at end
                where reconciliations.office_id = %(o)s
                """,
                {"o": office_id, "c": case_id, "comp": comp, "rule": r.rule, "desc": r.description,
                 "ll": r.left_label, "lv": r.left_value, "rl": r.right_label, "rv": r.right_value,
                 "diff": r.diff, "tol": r.tolerance, "status": r.status, "details": Jsonb(r.details)},
            )
        existing = conn.execute(
            "select id, competence, rule from reconciliations where case_id = %s and office_id = %s",
            (case_id, office_id),
        ).fetchall()
        for row in existing:
            if (row["competence"], row["rule"]) not in keep:
                conn.execute("delete from reconciliations where id = %s and office_id = %s", (row["id"], office_id))


# ---------------------------------------------------------------- exportação
def get_snapshot(conn: psycopg.Connection, snapshot_id, office_id) -> dict[str, Any] | None:
    return conn.execute(
        "select id, case_id, content, sha256, created_at from snapshots where id = %s and office_id = %s",
        (snapshot_id, office_id),
    ).fetchone()


# ---------------------------------------------------------------- motor tributário (ciclo 2)
def get_case_snapshot(conn: psycopg.Connection, case_id, office_id) -> dict[str, Any] | None:
    return conn.execute(
        "select s.id, s.case_id, s.content, s.sha256 from snapshots s "
        "join tax_cases c on c.id = s.case_id and c.office_id = s.office_id "
        "where s.case_id = %s and s.office_id = %s and c.status = 'homologated'",
        (case_id, office_id),
    ).fetchone()


def upsert_suggestions(conn: psycopg.Connection, case_id, office_id, rows: list[dict]) -> int:
    """Grava as sugestões. Premissa já confirmada só volta a pendente se a sugestão mudou; premissas que deixaram
    de ser sugeridas (atividade renomeada, perfil sem Fator R) são removidas — a confirmação segue na auditoria."""
    with conn.transaction():
        conn.execute(
            "delete from assumptions where case_id = %s and office_id = %s "
            "and not ((key, scope) in (select * from unnest(%s::text[], %s::text[])))",
            (case_id, office_id, [r["key"] for r in rows], [r["scope"] for r in rows]),
        )
        for r in rows:
            conn.execute(
                """
                insert into assumptions (office_id, case_id, key, scope, grp, label, value_type, choices,
                                         suggested_value, suggested_origin)
                values (%(o)s, %(c)s, %(key)s, %(scope)s, %(group)s, %(label)s, %(value_type)s, %(choices)s,
                        %(suggested)s, %(origin)s)
                on conflict (case_id, key, scope) do update set
                  grp = excluded.grp, label = excluded.label, value_type = excluded.value_type,
                  choices = excluded.choices, suggested_origin = excluded.suggested_origin, updated_at = now(),
                  status = case when assumptions.suggested_value is distinct from excluded.suggested_value
                                then 'pending' else assumptions.status end,
                  suggested_value = excluded.suggested_value
                where assumptions.office_id = %(o)s
                """,
                {"o": office_id, "c": case_id, "key": r["key"], "scope": r["scope"], "group": r["group"],
                 "label": r["label"], "value_type": r["value_type"], "choices": Jsonb(r["choices"]),
                 "suggested": Jsonb(r["suggested_value"]), "origin": Jsonb(r["suggested_origin"])},
            )
    return len(rows)


def load_assumptions(conn: psycopg.Connection, case_id, office_id) -> list[dict[str, Any]]:
    return conn.execute(
        "select key, scope, grp, label, suggested_value, value, status, justification, confirmed_at from assumptions "
        "where case_id = %s and office_id = %s order by key, scope",
        (case_id, office_id),
    ).fetchall()


def find_simulation(conn: psycopg.Connection, case_id, office_id, snapshot_sha: str, assumptions_hash: str,
                    rules_hash: str) -> dict[str, Any] | None:
    return conn.execute(
        "select id, status from simulations where case_id = %s and office_id = %s and snapshot_sha256 = %s "
        "and assumptions_hash = %s and rules_hash = %s",
        (case_id, office_id, snapshot_sha, assumptions_hash, rules_hash),
    ).fetchone()


def save_simulation(conn: psycopg.Connection, *, case_id, office_id, snapshot_id, snapshot_sha: str,
                    assumptions_hash: str, rules_version: str, rules_hash: str, status: str, result: dict,
                    result_hash: str | None, lines: list[dict], assumptions: list[dict], requested_by=None,
                    duration_ms: int | None = None, error_code: str | None = None, error_message: str | None = None):
    """Grava a simulação com a cópia das premissas usadas (a mesma lista que gerou `assumptions_hash`)."""
    with conn.transaction():
        row = conn.execute(
            """
            insert into simulations (office_id, case_id, snapshot_id, snapshot_sha256, assumptions_hash, rules_version,
                                     rules_hash, status, result_hash, result, assumptions, error_code, error_message,
                                     requested_by, duration_ms)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (case_id, snapshot_sha256, assumptions_hash, rules_hash) do nothing
            returning id
            """,
            (office_id, case_id, snapshot_id, snapshot_sha, assumptions_hash, rules_version, rules_hash, status,
             result_hash, Jsonb(result), Jsonb(assumptions), error_code, error_message, requested_by, duration_ms),
        ).fetchone()
        if row is None:
            return None
        with conn.cursor() as cur:
            cur.executemany(
                "insert into simulation_lines (office_id, simulation_id, ordinal, regime, period, tax, kind, base, rate, "
                "amount, formula, rule_ref, origin, activity, partial, verified) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [(office_id, row["id"], i, l["regime"], l["period"], l["tax"], l["kind"], l["base"], l["rate"],
                  l["amount"], l["formula"], l["rule_ref"], Jsonb(l["origin"]), l["activity"], l["partial"],
                  l["verified"]) for i, l in enumerate(lines)],
            )
        return row["id"]


def get_simulation(conn: psycopg.Connection, simulation_id, office_id) -> dict[str, Any] | None:
    return conn.execute(
        "select id, case_id, status, result, result_hash, rules_version, rules_hash, snapshot_sha256, "
        "assumptions_hash, assumptions, created_at from simulations where id = %s and office_id = %s",
        (simulation_id, office_id),
    ).fetchone()


def get_simulation_lines(conn: psycopg.Connection, simulation_id, office_id) -> list[dict[str, Any]]:
    return conn.execute(
        "select regime, period, tax, kind, base, rate, amount, formula, rule_ref, origin, activity, partial, verified "
        "from simulation_lines where simulation_id = %s and office_id = %s order by ordinal",
        (simulation_id, office_id),
    ).fetchall()
