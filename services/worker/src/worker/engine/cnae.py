"""Tabela CNAE → anexo do Simples (sugestão do perfil da atividade no planejamento rápido).

Versão e hash próprios, fora do hash das regras tributárias (não invalida os goldens de 2026/2027). Casamento pelo
prefixo mais longo dos 7 dígitos do CNAE; sem prefixo, não há sugestão e o analista escolhe o anexo."""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from worker.engine.activities import ActivityProfile
from worker.engine.rules import RulesError

ANEXOS = ("I", "II", "III", "IV", "V")


@dataclass(frozen=True)
class CnaeMatch:
    cnae: str
    prefixo: str
    profile: ActivityProfile
    vedado: bool
    nota: str


@dataclass(frozen=True)
class CnaeTable:
    version: str
    hash: str
    verified: bool
    source: str
    entries: dict           # prefixo → entrada

    def match(self, cnae: str | None) -> CnaeMatch | None:
        code = "".join(ch for ch in str(cnae or "") if ch.isdigit())
        if len(code) != 7:
            return None
        for size in range(7, 1, -1):
            e = self.entries.get(code[:size])
            if e:
                profile = ActivityProfile(e["anexo"], e["presumido"], False, bool(e["fator_r"]))
                return CnaeMatch(code, e["prefixo"], profile, bool(e["vedado"]), e["nota"])
        return None


def format_cnae(cnae: str | None) -> str:
    """"4744001" → "4744-0/01"."""
    code = "".join(ch for ch in str(cnae or "") if ch.isdigit())
    return f"{code[:4]}-{code[4]}/{code[5:]}" if len(code) == 7 else str(cnae or "")


def load_cnae_table(path: str | Path) -> CnaeTable:
    path = Path(path)
    if not path.is_file():
        raise RulesError(f"tabela CNAE → anexo ausente: {path}")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RulesError(f"JSON inválido em {path}: {exc}") from exc
    entries = {}
    for e in doc["entradas"]:
        prefixo = str(e["prefixo"])
        if not prefixo.isdigit() or not 2 <= len(prefixo) <= 7 or e["anexo"] not in ANEXOS or prefixo in entries:
            raise RulesError(f"entrada inválida na tabela CNAE: {prefixo}")
        entries[prefixo] = e
    return CnaeTable(doc["versao"], hashlib.sha256(raw).hexdigest(), bool(doc.get("verificado", False)),
                     doc.get("fonte", ""), entries)
