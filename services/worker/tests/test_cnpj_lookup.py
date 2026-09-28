"""Ciclo 5 — AT-508, AT-509: consulta de CNAE pela automação n8n (MCP) com transporte simulado.

A resposta simulada reproduz o formato observado na automação (texto JSON com uma lista de um objeto da BrasilAPI),
com um sócio fictício para provar que ele é descartado."""
import json

import httpx
import pytest

from worker.cnpj_lookup import LookupError_, consultar_cnpj

URL = "https://mcp.example.test/mcp/consulta-cnpj"
PAYLOAD = [{
    "cnpj": "37704456000142", "razao_social": "EMPRESA TESTE LTDA",
    "cnae_fiscal": 4744001, "cnae_fiscal_descricao": "Comércio varejista de ferragens e ferramentas",
    "cnaes_secundarios": [{"codigo": 4742300, "descricao": "Comércio varejista de material elétrico"},
                          {"codigo": 0, "descricao": ""}],
    "qsa": [{"nome_socio": "SOCIO FICTICIO", "cnpj_cpf_do_socio": "***123456**"}],
    "email": "contato@example.test",
}]


def sse(message: dict) -> str:
    return "event: message\ndata: " + json.dumps(message) + "\n\n"


def transport(tool_result=None, status=200, error=None, fail_on=None):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        method = body.get("method")
        if fail_on == method:
            raise httpx.ReadTimeout("timeout", request=request)
        if method == "initialize":
            return httpx.Response(200, headers={"Mcp-Session-Id": "s-1", "Content-Type": "text/event-stream"},
                                  text=sse({"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {"tools": {}}}}))
        if method == "notifications/initialized":
            return httpx.Response(202)
        assert request.headers["Mcp-Session-Id"] == "s-1"
        assert body["params"] == {"name": "Consultar_CNPJ", "arguments": {"cnpj": "37704456000142"}}
        msg = {"jsonrpc": "2.0", "id": 2}
        msg.update({"error": error} if error else {"result": tool_result})
        return httpx.Response(status, headers={"Content-Type": "text/event-stream"}, text=sse(msg))
    return httpx.MockTransport(handler)


def test_extracts_only_cnae_and_name():
    result = {"content": [{"type": "text", "text": json.dumps(PAYLOAD)}]}
    data = consultar_cnpj(URL, "37.704.456/0001-42", transport=transport(result))
    assert data == {"razao_social": "EMPRESA TESTE LTDA", "cnae_principal": "4744001",
                    "cnae_descricao": "Comércio varejista de ferragens e ferramentas",
                    "cnaes_secundarios": [{"codigo": "4742300", "descricao": "Comércio varejista de material elétrico"}]}
    assert "qsa" not in json.dumps(data) and "SOCIO" not in json.dumps(data)


def test_object_payload_is_accepted():
    result = {"content": [{"type": "text", "text": json.dumps(PAYLOAD[0])}]}
    assert consultar_cnpj(URL, "37704456000142", transport=transport(result))["cnae_principal"] == "4744001"


@pytest.mark.parametrize("kwargs, message", [
    ({"tool_result": {"content": [{"type": "text", "text": json.dumps([{"razao_social": "X"}])}]}}, "sem CNAE"),
    ({"tool_result": {"isError": True, "content": [{"type": "text", "text": "erro"}]}}, "devolveu erro"),
    ({"error": {"code": -32000, "message": "falhou"}}, "erro MCP"),
    ({"tool_result": {}, "status": 502}, "HTTP 502"),
    ({"fail_on": "tools/call"}, "ReadTimeout"),
])
def test_failures_raise_lookup_error(kwargs, message):
    with pytest.raises(LookupError_, match=message):
        consultar_cnpj(URL, "37704456000142", transport=transport(**kwargs))


def test_invalid_cnpj_is_rejected_before_calling():
    with pytest.raises(LookupError_, match="CNPJ inválido"):
        consultar_cnpj(URL, "123", transport=transport({}))


def test_env_file_does_not_override_environment(tmp_path, monkeypatch):
    """O .env local completa o ambiente, mas nunca sobrescreve variável já definida (ex.: a URL anulada nos testes)."""
    from worker.config import load_env_file

    env = tmp_path / ".env"
    env.write_text("# comentário\nCNPJ_LOOKUP_MCP_URL=https://do-arquivo.example\nZZ_TESTE_CHAVE='valor'\n", encoding="utf-8")
    monkeypatch.setenv("CNPJ_LOOKUP_MCP_URL", "")
    monkeypatch.delenv("ZZ_TESTE_CHAVE", raising=False)
    load_env_file(env)
    import os

    assert os.environ["CNPJ_LOOKUP_MCP_URL"] == ""
    assert os.environ["ZZ_TESTE_CHAVE"] == "valor"
    monkeypatch.delenv("ZZ_TESTE_CHAVE")
