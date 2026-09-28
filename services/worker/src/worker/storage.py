"""Download/upload no Supabase Storage via REST com a chave de serviço."""
from typing import Protocol

import httpx

from worker.errors import FileNotFound, TransientError

TIMEOUT = httpx.Timeout(30.0)


class Storage(Protocol):
    def download(self, path: str) -> bytes: ...

    def upload(self, path: str, data: bytes, content_type: str) -> None: ...

    def delete(self, paths: list[str]) -> None: ...

    def list_prefix(self, prefix: str) -> list[str]: ...


class SupabaseStorage:
    def __init__(self, supabase_url: str, service_role_key: str, bucket: str):
        self.root = supabase_url.rstrip("/") + "/storage/v1/object/"
        self.bucket = bucket
        self.base = self.root + bucket + "/"
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

    def _call(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            resp = httpx.request(method, url, headers={**self.headers, "Content-Type": "application/json"},
                                 timeout=TIMEOUT, **kwargs)
        except httpx.HTTPError as exc:
            raise TransientError("falha de rede no Storage: " + type(exc).__name__) from exc
        if resp.status_code >= 500:
            raise TransientError("Storage respondeu " + str(resp.status_code))
        resp.raise_for_status()
        return resp

    def list_prefix(self, prefix: str) -> list[str]:
        """Caminhos de todos os objetos sob `prefix` (desce nas subpastas)."""
        out, folders = [], [prefix.rstrip("/")]
        while folders:
            folder = folders.pop()
            offset = 0
            while True:
                items = self._call("POST", self.root + "list/" + self.bucket,
                                   json={"prefix": folder, "limit": 1000, "offset": offset}).json()
                for it in items:
                    path = folder + "/" + it["name"]
                    (out if it.get("id") else folders).append(path)
                if len(items) < 1000:
                    break
                offset += 1000
        return out

    def delete(self, paths: list[str]) -> None:
        for i in range(0, len(paths), 1000):
            self._call("DELETE", self.root + self.bucket, json={"prefixes": paths[i:i + 1000]})
