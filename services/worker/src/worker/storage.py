"""Download/upload no Supabase Storage via REST com a chave de serviço."""
from typing import Protocol

import httpx

from worker.errors import FileNotFound, TransientError

TIMEOUT = httpx.Timeout(30.0)


class Storage(Protocol):
    def download(self, path: str) -> bytes: ...

    def upload(self, path: str, data: bytes, content_type: str) -> None: ...


class SupabaseStorage:
    def __init__(self, supabase_url: str, service_role_key: str, bucket: str):
        self.base = supabase_url.rstrip("/") + "/storage/v1/object/" + bucket + "/"
        self.headers = {"Authorization": "Bearer " + service_role_key, "apikey": service_role_key}

    def download(self, path: str) -> bytes:
        try:
            resp = httpx.get(self.base + path, headers=self.headers, timeout=TIMEOUT)
        except httpx.HTTPError as exc:
            raise TransientError("falha de rede no Storage: " + type(exc).__name__) from exc
        if resp.status_code in (400, 404):
            raise FileNotFound("objeto não encontrado no Storage")
        if resp.status_code >= 500:
            raise TransientError("Storage respondeu " + str(resp.status_code))
        resp.raise_for_status()
        return resp.content

    def upload(self, path: str, data: bytes, content_type: str) -> None:
        headers = {**self.headers, "Content-Type": content_type, "x-upsert": "true"}
        try:
            resp = httpx.post(self.base + path, headers=headers, content=data, timeout=TIMEOUT)
        except httpx.HTTPError as exc:
            raise TransientError("falha de rede no Storage: " + type(exc).__name__) from exc
        if resp.status_code >= 500:
            raise TransientError("Storage respondeu " + str(resp.status_code))
        resp.raise_for_status()
