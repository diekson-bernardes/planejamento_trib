"""Carga, validação e consulta das regras versionadas (services/worker/rules/<exercício>/)."""
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from worker.engine.memory import D


class RulesError(Exception):
    """Arquivo de regras ausente, inválido ou incoerente: o worker não deve iniciar."""


class MissingRule(Exception):
    """Não há regra ou premissa aplicável (vigência, anexo, faixa, perfil): o regime fica "não calculado"."""


@dataclass(frozen=True)
class Band:
    anexo: str
    faixa: int
    ate: Decimal
    nominal: Decimal
    deduzir: Decimal
    shares: dict                      # tributo → percentual de repartição
    iss_excess: dict | None = None    # 5ª faixa acima do teto de ISS: limiar + repartição do excedente

    def share(self, tax: str) -> Decimal:
        return self.shares.get(tax, Decimal("0"))


@dataclass(frozen=True)
class Anexo:
    code: str
    taxes: tuple
    bands: tuple
    cpp_fora_do_das: bool

    def band_for(self, rbt12: Decimal) -> Band | None:
        for band in self.bands:
            if rbt12 <= band.ate:
                return band
        return None

    def band_number(self, n: int) -> Band:
        return next(b for b in self.bands if b.faixa == n)


@dataclass(frozen=True)
class RuleSet:
    version: str
    hash: str
    exercise: int
    start: date
    end: date
    simples: dict        # dados brutos do simples.json (limites, flags)
    anexos: dict         # código → Anexo
    presumido: dict
    real: dict
    encargos: dict
    elegibilidade: dict
    atividades: dict
    verified: dict       # domínio → bool

    def in_force(self, competence: str) -> bool:
        y, m = int(competence[:4]), int(competence[5:7])
        return self.start <= date(y, m, 1) <= self.end

    def ref(self, *parts) -> str:
        return ".".join(str(p) for p in parts) + "@" + self.version


def _check_shares(anexo: str, faixa: int, shares: list, taxes: list) -> None:
    if len(shares) != len(taxes):
        raise RulesError(f"simples anexo {anexo} faixa {faixa}: repartição com {len(shares)} colunas, esperado {len(taxes)}")
    total = sum((D(s) for s in shares), Decimal("0"))
    if abs(total - 1) > Decimal("0.0001"):
        raise RulesError(f"simples anexo {anexo} faixa {faixa}: repartição soma {total}")


def _anexos(simples: dict) -> dict:
    out = {}
    for code, raw in simples["anexos"].items():
        taxes = list(raw["tributos"])
        bands = []
        previous = Decimal("0")
        for f in raw["faixas"]:
            _check_shares(code, f["faixa"], f["reparticao"], taxes)
            excess = None
            if "iss_acima_do_teto" in f:
                ex = f["iss_acima_do_teto"]
                _check_shares(code, f["faixa"], ex["reparticao_do_excedente"], taxes)
                excess = {
                    "limiar": D(ex["limiar_efetiva"]),
                    "shares": {t: D(s) for t, s in zip(taxes, ex["reparticao_do_excedente"])},
                }
            ate = D(f["ate"])
            if ate <= previous:
                raise RulesError(f"simples anexo {code}: faixas fora de ordem")
            previous = ate
            bands.append(Band(code, int(f["faixa"]), ate, D(f["nominal"]), D(f["deduzir"]),
                              {t: D(s) for t, s in zip(taxes, f["reparticao"])}, excess))
        out[code] = Anexo(code, tuple(taxes), tuple(bands), bool(raw.get("cpp_fora_do_das", False)))
    return out


def load_rules(rules_dir: str | Path, exercise: str | int = "2026") -> RuleSet:
    base = Path(rules_dir) / str(exercise)
    manifest_path = base / "manifest.json"
    if not manifest_path.is_file():
        raise RulesError(f"manifest de regras ausente: {manifest_path}")
    digest = hashlib.sha256()
    manifest_bytes = manifest_path.read_bytes().replace(b"\r\n", b"\n")
    digest.update(manifest_bytes)
    manifest = json.loads(manifest_bytes)
    docs = {}
    for name in manifest["arquivos"]:
        path = base / name
        if not path.is_file():
            raise RulesError(f"arquivo de regras ausente: {path}")
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(b"\x00" + name.encode() + b"\x00" + raw)
        try:
            docs[path.stem] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RulesError(f"JSON inválido em {path}: {exc}") from exc

    required = ("simples", "presumido", "real", "encargos", "elegibilidade", "atividades")
    missing = [r for r in required if r not in docs]
    if missing:
        raise RulesError("domínios de regra ausentes: " + ", ".join(missing))

    start, end = (date.fromisoformat(d) for d in manifest["vigencia"])
    return RuleSet(
        version=manifest["version"],
        hash=digest.hexdigest(),
        exercise=int(manifest["exercicio"]),
        start=start,
        end=end,
        simples=docs["simples"],
        anexos=_anexos(docs["simples"]),
        presumido=docs["presumido"],
        real=docs["real"],
        encargos=docs["encargos"],
        elegibilidade=docs["elegibilidade"],
        atividades=docs["atividades"],
        verified={k: bool(v.get("verificado", False)) for k, v in docs.items()},
    )
