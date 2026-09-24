"""Loop do worker: polling da fila de jobs com lease, backoff e shutdown gracioso."""
import signal
import time

import psycopg

from worker import db
from worker.config import load_settings
from worker.pipeline import Pipeline, log
from worker.storage import SupabaseStorage

_stop = False


def _request_stop(signum, _frame) -> None:
    global _stop
    _stop = True
    log("worker.stopping", signal=signum)


def main() -> None:
    settings = load_settings()
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)
    storage = SupabaseStorage(settings.supabase_url, settings.service_role_key, settings.storage_bucket)
    log("worker.started", poll_seconds=settings.poll_seconds, max_attempts=settings.max_attempts)
    conn = None
    while not _stop:
        try:
            if conn is None or conn.closed:
                conn = db.connect(settings.database_url)
            pipeline = Pipeline(conn, storage)
            if not pipeline.run_once(settings.lease_seconds, settings.max_attempts):
                time.sleep(settings.poll_seconds)
        except psycopg.OperationalError as exc:
            log("worker.db_unavailable", error=type(exc).__name__)
            if conn is not None:
                conn.close()
            conn = None
            time.sleep(min(30.0, settings.poll_seconds * 5))
    if conn is not None:
        conn.close()
    log("worker.stopped")


if __name__ == "__main__":
    main()
