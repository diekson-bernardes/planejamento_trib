"""Parâmetros de decisão (rules/decisao.json): versão e hash próprios, fora do hash das regras tributárias."""
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from worker.engine.memory import D
from worker.engine.rules import RulesError


@dataclass(frozen=True)
class Variable:
    key: str
    label: str
    kind: str            # multiplicador | absoluto
    low: Decimal
    high: Decimal
    unit: str = "reais"      # reais | fracao — unidade do valor base quando o tipo é multiplicador


@dataclass(frozen=True)
class DecisionParams:
    version: str
    hash: str
    year: int
    default_threshold: Decimal
    robust_above: Decimal
    fragile_below: Decimal
    proportional_keys: tuple
    grid_points: int
    bisection_steps: int
    precision: Decimal
    variables: tuple
    load_groups: dict      # consumo | renda | folha → tributos
    caveats: tuple

    def robustness(self, distance: Decimal | None) -> str | None:
        if distance is None:
            return None
        if distance > self.robust_above:
            return "robusta"
        if distance < self.fragile_below:
            return "fragil"
        return "atencao"


def load_decision_params(path: str | Path) -> DecisionParams:
    path = Path(path)
    if not path.is_file():
        raise RulesError(f"parâmetros de decisão ausentes: {path}")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RulesError(f"JSON inválido em {path}: {exc}") from exc
    sens = doc["sensibilidade"]
    variables = tuple(Variable(v["chave"], v["rotulo"], v["tipo"], D(v["de"]), D(v["ate"]), v.get("unidade", "reais"))
                      for v in sens["variaveis"])
    for v in variables:
        if v.kind not in ("multiplicador", "absoluto") or v.low >= v.high:
            raise RulesError(f"variável de sensibilidade inválida: {v.key}")
    return DecisionParams(
        version=doc["versao"],
        hash=hashlib.sha256(raw).hexdigest(),
        year=int(doc["exercicio"]),
        default_threshold=D(doc["limiar_padrao"]),
        robust_above=D(doc["robustez"]["robusta_acima"]),
        fragile_below=D(doc["robustez"]["fragil_abaixo"]),
        proportional_keys=tuple(doc["projecao"]["campos_proporcionais_a_receita"]),
        grid_points=int(sens["busca"]["pontos_grade"]),
        bisection_steps=int(sens["busca"]["iteracoes_bissecao"]),
        precision=D(sens["busca"]["precisao_relativa"]),
        variables=variables,
        load_groups={k: tuple(v) for k, v in doc["carga"].items()},
        caveats=tuple(doc["ressalvas"]),
    )
