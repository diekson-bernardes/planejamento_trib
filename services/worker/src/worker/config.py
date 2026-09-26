"""Configuração do worker, lida exclusivamente de variáveis de ambiente."""
import os
from pathlib import Path

from pydantic import BaseModel, Field


# services/worker/rules (repositório); na imagem Docker, RULES_DIR=/app/rules
DEFAULT_RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


class Settings(BaseModel):
    database_url: str
    supabase_url: str = "http://127.0.0.1:54321"
    service_role_key: str = ""
    storage_bucket: str = "documents"
    poll_seconds: float = Field(default=2.0, gt=0)
    max_attempts: int = Field(default=3, ge=1)
    lease_seconds: int = Field(default=300, ge=10)
    rules_dir: str = str(DEFAULT_RULES_DIR)
    rules_exercise: str = "2026"
    decision_params: str = str(DEFAULT_RULES_DIR / "decisao.json")


def decision_params_path(settings: "Settings", year: int) -> str:
    """Política de decisão do exercício: `decisao.json` (2026) ou `decisao_<ano>.json` na mesma pasta."""
    if year <= 2026:
        return settings.decision_params
    return os.path.join(os.path.dirname(settings.decision_params), f"decisao_{year}.json")


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        ),
        supabase_url=os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321"),
        service_role_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        storage_bucket=os.environ.get("STORAGE_BUCKET", "documents"),
        poll_seconds=float(os.environ.get("WORKER_POLL_SECONDS", "2")),
        max_attempts=int(os.environ.get("WORKER_MAX_ATTEMPTS", "3")),
        lease_seconds=int(os.environ.get("WORKER_LEASE_SECONDS", "300")),
        rules_dir=os.environ.get("RULES_DIR", str(DEFAULT_RULES_DIR)),
        rules_exercise=os.environ.get("RULES_EXERCISE", "2026"),
        decision_params=os.environ.get(
            "DECISION_PARAMS", os.path.join(os.environ.get("RULES_DIR", str(DEFAULT_RULES_DIR)), "decisao.json")
        ),
    )
