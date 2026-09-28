"""Consulta de CNAE pela automação n8n (servidor MCP, ferramenta `Consultar_CNPJ`, dados da BrasilAPI).

Protocolo MCP sobre HTTP (JSON-RPC; respostas em `text/event-stream`): initialize → notifications/initialized →
tools/call. Só CNAE e razão social saem daqui — sócios (QSA) e demais campos são descartados em memória."""
import json

import httpx

HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
TOOL = "Consultar_CNPJ"


class LookupError_(Exception):
    """Falha da consulta (rede, timeout, erro do servidor MCP ou resposta sem CNAE)."""


def _rpc(method: str, params: dict | None = None, id_: int | None = None) -> dict:
    msg: dict = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    if id_ is not None:
        msg["id"] = id_
    return msg


def _message(resp: httpx.Response) -> dict:
    """Última mensagem JSON-RPC da resposta (SSE `data:` ou JSON puro)."""
    if resp.status_code >= 400:
        raise LookupError_(f"HTTP {resp.status_code}")
    text = resp.text
    data = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
    try:
        msg = json.loads(data[-1] if data else text)
    except (json.JSONDecodeError, IndexError) as exc:
        raise LookupError_("resposta MCP inválida") from exc
    if "error" in msg:
        raise LookupError_("erro MCP: " + str(msg["error"].get("message", ""))[:200])
    return msg


def _digits(value) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def parse_payload(result: dict) -> dict:
    """Resultado de tools/call → só CNAE/razão social. Aceita o JSON da BrasilAPI como objeto ou lista de um item."""
    if result.get("isError"):
        raise LookupError_("a ferramenta Consultar_CNPJ devolveu erro")
    content = result.get("content") or []
    text = next((c.get("text") for c in content if c.get("type") == "text"), None)
    try:
        payload = json.loads(text or "")
    except json.JSONDecodeError as exc:
        raise LookupError_("resposta sem JSON da consulta de CNPJ") from exc
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    cnae = _digits(payload.get("cnae_fiscal"))
    if len(cnae) != 7:
        raise LookupError_("resposta sem CNAE principal")
    secundarios = []
    for c in payload.get("cnaes_secundarios") or []:
        code = _digits(c.get("codigo"))
        if len(code) == 7:
            secundarios.append({"codigo": code, "descricao": c.get("descricao")})
    return {"razao_social": payload.get("razao_social"), "cnae_principal": cnae,
            "cnae_descricao": payload.get("cnae_fiscal_descricao"), "cnaes_secundarios": secundarios}


def consultar_cnpj(url: str, cnpj: str, timeout: float = 20.0, transport: httpx.BaseTransport | None = None) -> dict:
    cnpj = _digits(cnpj)
    if len(cnpj) != 14:
        raise LookupError_("CNPJ inválido")
    headers = dict(HEADERS)
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            init = client.post(url, headers=headers, json=_rpc("initialize", {
                "protocolVersion": "2025-03-26", "capabilities": {},
                "clientInfo": {"name": "planejamento-trib", "version": "1"}}, 1))
            _message(init)
            session = init.headers.get("Mcp-Session-Id")
            if session:
                headers["Mcp-Session-Id"] = session
            client.post(url, headers=headers, json=_rpc("notifications/initialized"))
            resp = client.post(url, headers=headers, json=_rpc("tools/call", {"name": TOOL, "arguments": {"cnpj": cnpj}}, 2))
            return parse_payload(_message(resp).get("result") or {})
    except httpx.HTTPError as exc:
        raise LookupError_(type(exc).__name__) from exc
