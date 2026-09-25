"""Configuração do worker, lida exclusivamente de variáveis de ambiente."""
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    database_url: str
    supabase_url: str = "http://127.0.0.1:54321"
    service_role_key: str = ""
    storage_bucket: str = "documents"
    poll_seconds: float = Field(default=2.0, gt=0)
    max_attempts: int = Field(default=3, ge=1)
    lease_seconds: int = Field(default=300, ge=10)


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
    )
