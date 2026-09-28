# DESIGN: Planejamento Rápido (ciclo 5)

> Technical design for implementing Planejamento Rápido — dossiê de 2027 a partir da Declaração de Faturamento, folha e DRE (PDF ou digitados), com CNAE consultado pela automação n8n e anexo sugerido por tabela CNAE → anexo.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | PLANEJAMENTO_RAPIDO |
| **Date** | 2026-09-26 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_PLANEJAMENTO_RAPIDO.md` |
| **DEFINE** | `sdd/DEFINE_PLANEJAMENTO_RAPIDO.md` |
| **UX REVIEW** | N/A |
| **LLM Prompts** | false |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
 Analista (web)                         Automação n8n (MCP Server Trigger)
   │  cria dossiê kind='rapido'            ▲  tools/call Consultar_CNPJ (cnpj)
   │  upload PDF / digitação               │  (HTTP + SSE, sem auth, timeout 20 s)
   │  "Consultar CNAE" ─────► request_company_lookup ─► job lookup_company ─► cnpj_lookup.py
   ▼                                                                         │ grava CNAE (sem sócios)
 Supabase (Postgres + Storage)                                               ▼
   source_files (DECLARACAO_FATURAMENTO | FOLHA_ALTERDATA | DRE_ALTERDATA)  companies.cnae_*
   manual_values (faturamento/folha/DRE digitados, autor + data)
   tax_cases.kind = 'rapido'
   │  job extract (parser declaracao_faturamento.py + parsers Alterdata)
   │  homologate_case (bloqueios do rápido; snapshot com valores digitados)
   ▼
 Worker
   suggest ─► quick_view.py ─► SnapshotView sintético (PGDAS_D/FOLHA/DRE/BALANCETE por mês)
              ▲ rules/cnae_anexos.json (perfil sugerido)   │
              │ premissas rapido.* + atividade.perfil       ▼
   project(year=2027) ─► quick_view ─► build_projection ─► shift_year ─► calculate(regimes sem REAL)
              ─► sensibilidade ─► recomendação ─► projections/projection_lines ─► aprovação RT ─► PDF
```

---

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| Tipo de dossiê rápido | Distinguir o fluxo do planejamento rápido | Coluna `tax_cases.kind` (`completo`/`rapido`) | Criação do dossiê | Regras de homologação e projeção por tipo | Migration |
| Parser da Declaração de Faturamento | Extrair CNPJ, período, 12 meses e Total Geral com origem | Python, `ValueCollector` e âncoras como os parsers Alterdata | PDF | `ParseResult` (doc `DECLARACAO_FATURAMENTO`) | `classify.py`, `pdf/layout.py` |
| Validações da declaração | Soma = Total Geral; 12 meses consecutivos | Função em `validations.py` | `ParseResult` | `ValidationResult` | Parser |
| Valores digitados | Faturamento/folha/DRE sem PDF, com autor e data | Tabela `manual_values` + RPC `enter_manual_values` | Formulário web | Linhas incluídas no snapshot | Migration, RLS |
| Homologação do rápido | Bloqueios próprios e snapshot com valores digitados | `homologate_case` redefinida | Arquivos, valores, digitação | Snapshot com hash | Migration |
| Consulta de CNAE | Obter CNAE principal/secundários pela automação n8n | Cliente MCP mínimo (JSON-RPC sobre HTTP/SSE) com `httpx`; job `lookup_company` | CNPJ | `companies.cnae_*` | Automação n8n |
| Tabela CNAE → anexo | Sugerir perfil (anexo, presunção, Fator R, vedação) | `rules/cnae_anexos.json` com versão/hash próprios, casamento por prefixo mais longo | CNAE | `ActivityProfile` sugerido | LC 123/2006, Resolução CGSN 140/2018 (fontes secundárias) |
| Adaptador do snapshot rápido | Produzir o conteúdo que o motor lê (PGDAS_D/FOLHA/DRE/BALANCETE por mês) | `engine/quick_view.py`, reaproveitando `_synthetic_month` da projeção | Snapshot rápido + premissas | `SnapshotView` sintético | `projection.py` |
| Premissas do rápido | % ICMS-ST, % monofásico, ICMS no regime normal, perfil por CNAE | `assumptions.py` (grupo `rapido`) | `quick_view` + tabela CNAE | Sugestões | Tabela CNAE |
| Faixa do Simples | Informar faixa, nominal, parcela a deduzir e efetiva | Linha `informativo` `faixa` por anexo e mês em `simples.py` | RBT12 e anexo | Linha na memória, tela e PDF | Regras do Simples |
| Cálculo sem Real | Três alternativas no rápido | Parâmetro `regimes` em `calculate`/`project` | Tipo do dossiê | Simulação sem `REAL` | Motor do ciclo 4 |
| Telas | Criar dossiê rápido, digitar valores, consultar CNAE, ver faixa | Next.js server actions + componentes existentes | Ações do analista | RPCs | Migration, tipos |

---

## Key Decisions

### Decision 1: Snapshot sintético em vez de mudar o motor

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-26 |
| **Source** | DEFINE (motor e regras não mudam) + evidência no código (`SnapshotView.complete_competences`, `activities`, `revenue_series` dependem do PGDAS-D) |

**Context:** o motor, a projeção e as premissas leem receita, séries, RBAA e atividades do PGDAS-D e só consideram competências com PGDAS-D, folha, DRE e balancete.

**Choice:** `quick_view(content, confirmed, cnae_rules)` converte o snapshot homologado do dossiê rápido em conteúdo sintético no formato atual: para cada mês com folha e DRE gera PGDAS_D (RPA, séries `receita_anterior.*` da declaração, RBAA, atividades), FOLHA, DRE e um BALANCETE vazio (marcador de competência completa), reaproveitando `_synthetic_month`; os demais meses da declaração entram só nas séries de receita (viram "estimados" na projeção).

**Rationale:** mantém `build_projection`, `shift_year`, `calculate`, sensibilidade e recomendação intactos; os quatro goldens anteriores seguem protegidos.

**Alternatives Rejected:**
1. Ensinar o motor a ler a declaração diretamente — espalharia `if kind == 'rapido'` pelo motor e arriscaria os goldens.
2. Calculadora anual separada — rejeitada no Brainstorm (duplicaria regras).

**Consequences:**
- O snapshot homologado guarda os dados reais (declaração, folha, DRE, digitação); o conteúdo sintético é derivado e refeito a cada sugestão/projeção.
- As atividades sintéticas dependem das premissas de perfil, % ST e % monofásico (confirmadas depois da homologação).

### Decision 2: Atividades sintéticas por CNAE com variantes de ST e monofásico

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-26 |
| **Source** | DEFINE (A-503: 100% no CNAE principal) + código (`Activity.key` distingue tributos zerados) |

**Context:** o Simples depende da receita por atividade e dos tributos zerados (ST, monofásico); sem PGDAS-D não há essa divisão.

**Choice:** para o CNAE principal, três atividades com chaves estáveis — `cnae-4744001`, `cnae-4744001~zero-icms` (ICMS-ST) e `cnae-4744001~zero-cofins-pis` (monofásico) —, com receita = faturamento × (1 − %ST − %mono), × %ST e × %mono, pelas premissas `rapido.pct_icms_st` e `rapido.pct_monofasico` (padrão 0, confirmadas pelo analista). As premissas `atividade.perfil` e `atividade.tributos_zerados` existentes continuam por atividade.

**Rationale:** as chaves não mudam quando os percentuais mudam, então as premissas por atividade permanecem estáveis; o motor já trata tributos zerados.

**Alternatives Rejected:**
1. Distribuir receita entre CNAEs secundários — SHOULD do DEFINE, adiado (premissa por CNAE) para não bloquear o MVP.
2. Uma atividade só, sem ST/monofásico — subestimaria o efeito de ST em comércio.

**Consequences:**
- Atividades com percentual 0 ficam com receita 0 e não geram imposto.
- A soma dos percentuais acima de 100% é recusada na confirmação.

### Decision 3: Tabela CNAE → anexo fora do hash das regras tributárias

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-26 |
| **Source** | DEFINE (5b: todos os anexos, `verificado: false`) + ciclo 3 (política de decisão com versão/hash próprios) |

**Context:** incluir a tabela em `rules/2027/` mudaria a versão/hash das regras 2027 e invalidaria o golden `decisao_2027`.

**Choice:** `services/worker/rules/cnae_anexos.json` com `versao`, `fonte`, `verificado: false` e entradas por prefixo de CNAE (divisão, grupo, classe ou subclasse) → anexo, presunção, Fator R, vedação e nota; casamento pelo prefixo mais longo; exceções por subclasse. Carregado por `engine/cnae.py` com hash próprio gravado na origem da sugestão.

**Rationale:** mesma solução já adotada para `decisao.json`; a tabela sugere, o analista confirma.

**Alternatives Rejected:**
1. Tabela dentro de `rules/2027/` — mudaria o hash e a versão das regras 2027.
2. Mapeamento fixo em código — sem versão nem rastreabilidade.

**Consequences:**
- CNAE vedado (art. 17 da LC 123) sugere Simples inelegível, confirmável pelo analista.
- Revisão contábil da tabela entra como pendência, como as regras 2027.

### Decision 4: Valores digitados em tabela própria, incluídos no snapshot

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-26 |
| **Source** | DEFINE (AT-505, AT-506) + código (`source_files` exige `storage_path` e `sha256` de arquivo) |

**Context:** a digitação não tem arquivo; `source_files` modela PDFs no Storage.

**Choice:** tabela `manual_values(case_id, doc_type, competence, field_key, value, entered_by, entered_at)` gravada só pela RPC `enter_manual_values` (security definer), que recusa mês/documento com PDF extraído; `homologate_case` inclui essas linhas em `values` com `origin: "manual"`, autor e data, e protege a tabela com o gatilho de imutabilidade do dossiê homologado.

**Rationale:** rastreabilidade (quem/quando) sem fingir arquivo; o adaptador lê PDF e digitação com as mesmas chaves normalizadas.

**Alternatives Rejected:**
1. `source_file` sintético por digitação — exigiria afrouxar `storage_path`/`sha256` e a política de upload.
2. Digitar direto como premissa — misturaria dado de entrada com premissa e perderia a homologação.

**Consequences:**
- Chaves normalizadas da digitação: `faturamento.mes`; `folha.salarios`, `folha.pro_labore`, `folha.autonomos`; `dre.receita_bruta`, `dre.outras_receitas`, `dre.resultado`.
- Alterar um valor extraído de PDF continua sendo ajuste justificado.

### Decision 5: Consulta de CNAE como job do worker com cliente MCP mínimo

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-26 |
| **Source** | DEFINE (4c, 8a, contrato MCP verificado) + código (worker já usa `httpx` e fila `jobs`) |

**Context:** a automação é um servidor MCP (n8n MCP Server Trigger) sem autenticação; a chamada é externa e pode falhar.

**Choice:** RPC `request_company_lookup(p_company_id)` enfileira `lookup_company`; o worker abre sessão (`initialize` → `notifications/initialized` → `tools/call` `Consultar_CNPJ`) em `cnpj_lookup.py` com `httpx` (timeout 20 s), lê a resposta SSE, extrai `cnae_fiscal`, `cnae_fiscal_descricao`, `cnaes_secundarios`, `razao_social` e grava em `companies`; descarta o resto (sócios). Falha → status `falhou` visível na tela e CNAE digitado pela RPC `set_company_cnae`.

**Rationale:** chamadas externas saem só do servidor, com retry da fila e logs por ID; sem dependência nova (MCP SDK) para uma única ferramenta.

**Alternatives Rejected:**
1. Chamar do navegador — exporia a URL e dependeria de CORS.
2. Server action do Next.js — duplicaria cliente HTTP e fugiria do padrão de jobs.

**Consequences:**
- O analista espera a fila (poll de 2 s) para ver o CNAE.
- URL em `CNPJ_LOOKUP_MCP_URL`; sem ela, a consulta é desativada e só a digitação aparece.

### Decision 6: Rápido projeta só 2027 e sem Lucro Real

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-26 |
| **Source** | DEFINE (exercício 2027; Real fora) |

**Context:** o motor de 2027 calcula quatro regimes via `regimes_for(rules)`.

**Choice:** `calculate(..., regimes=None)` e `project(..., regimes=None)` aceitam a lista de regimes; o pipeline passa `("SIMPLES", "PRESUMIDO", "SIMPLES_HIBRIDO")` quando `kind = 'rapido'`. `request_projection` recusa ano ≠ 2027 para dossiê rápido; `request_calculation` (simulação de 2026) é recusada no rápido.

**Rationale:** parâmetro opcional com padrão igual ao comportamento atual — goldens inalterados.

**Alternatives Rejected:**
1. Calcular o Real e esconder na tela — geraria linhas e recomendação com Real.
2. Regras 2027 separadas sem Real — duplicaria regras.

**Consequences:**
- Sensibilidade e recomendação passam a ver só três regimes no rápido.

### Decision 7: Faixa do Simples como linha informativa

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-26 |
| **Source** | DEFINE (AT-513) + código (linha `informativo` de RBT12 já existe) |

**Context:** a faixa, a alíquota nominal e a parcela a deduzir hoje só aparecem na fórmula.

**Choice:** `simples.calculate_month` acrescenta uma linha `kind="informativo"`, `tax="faixa"` por anexo e mês, com origem contendo anexo, faixa, RBT12, alíquota nominal, dedução e efetiva; vale para dossiê completo e rápido, por dentro e híbrido. Tela e PDF leem essas linhas.

**Rationale:** linhas informativas não entram nos totais — goldens de totais inalterados.

**Alternatives Rejected:**
1. Só no dossiê rápido — duas formas de mostrar a mesma informação.

**Consequences:**
- `result_hash` de novas projeções muda (linhas a mais); projeções já gravadas não são afetadas.

### Decision 8: ICMS no regime normal sugerido pelo proxy do DAS

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-26 |
| **Source** | Código (premissa `icms_regime_normal` do ciclo 2 usa o ICMS do DAS como proxy) |

**Context:** sem PGDAS-D não há ICMS declarado; o Presumido e o Simples acima do sublimite (caso da amostra) precisam do ICMS no regime normal.

**Choice:** sugestão mensal = receita sem ST × alíquota efetiva do anexo/faixa × repartição de ICMS da faixa (mesmo proxy do ciclo 2), pendente de confirmação, origem com a fórmula.

**Rationale:** coerente com o dossiê completo; o analista substitui pelo ICMS apurado quando tiver.

**Alternatives Rejected:**
1. Sem sugestão — bloquearia todo dossiê rápido até digitar 12 valores.

**Consequences:**
- Ressalva no PDF quando a premissa foi confirmada com o valor sugerido.

---

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `supabase/migrations/20260926000005_planejamento_rapido.sql` | Create | `tax_cases.kind`; doc_type `DECLARACAO_FATURAMENTO`; `manual_values` + RLS + imutabilidade; `companies.cnae_*`; RPCs `enter_manual_values`, `request_company_lookup`, `set_company_cnae`; `homologate_case` com bloqueios do rápido; `request_projection`/`request_calculation` por tipo | (general) | None |
| 2 | `supabase/tests/planejamento_rapido.test.sql` | Create | pgTAP: RLS de `manual_values`, digitação recusada com PDF, bloqueios de homologação, ano 2027 no rápido, CNAE sem sócios | (general) | 1 |
| 3 | `services/worker/rules/cnae_anexos.json` | Create | Tabela CNAE → anexo (I–V, Fator R, vedações), `verificado: false`, fonte | (general) | None |
| 4 | `services/worker/src/worker/engine/cnae.py` | Create | Carrega a tabela (versão/hash) e casa CNAE pelo prefixo mais longo | (general) | 3 |
| 5 | `services/worker/src/worker/models.py`, `classify.py`, `parsers/__init__.py` | Modify | Tipo `DECLARACAO_FATURAMENTO`, âncora "DECLARAÇÃO DE FATURAMENTO", registro do parser | (general) | None |
| 6 | `services/worker/src/worker/parsers/declaracao_faturamento.py` | Create | Parser: CNPJ, período, 12 meses (`faturamento.mes`), Total Geral | (general) | 5 |
| 7 | `services/worker/src/worker/validations.py` | Modify | Soma = Total Geral; 12 meses consecutivos | (general) | 6 |
| 8 | `services/worker/src/worker/engine/quick_view.py` | Create | Snapshot sintético do dossiê rápido (atividades por CNAE, séries, folha/DRE PDF ou digitados) | (general) | 4, 6 |
| 9 | `services/worker/src/worker/engine/projection.py` | Modify | Expor `_synthetic_month` para reuso (sem mudar comportamento) | (general) | None |
| 10 | `services/worker/src/worker/engine/assumptions.py` | Modify | Grupo `rapido`: perfil por CNAE, `rapido.pct_icms_st`, `rapido.pct_monofasico`, ICMS no regime normal pelo proxy, outras receitas da DRE | (general) | 4, 8 |
| 11 | `services/worker/src/worker/engine/simples.py` | Modify | Linha informativa `faixa` (anexo, faixa, nominal, dedução, efetiva) | (general) | None |
| 12 | `services/worker/src/worker/engine/calculate.py`, `engine/decision.py` | Modify | Parâmetro `regimes` opcional | (general) | None |
| 13 | `services/worker/src/worker/cnpj_lookup.py` | Create | Cliente MCP mínimo (`initialize`, `tools/call Consultar_CNPJ`, SSE) e extração só de CNAE/razão social | (general) | None |
| 14 | `services/worker/src/worker/config.py`, `db.py`, `pipeline.py` | Modify | `CNPJ_LOOKUP_MCP_URL`; job `lookup_company`; `kind` do dossiê; suggest/project do rápido via `quick_view`; sem reconcile no rápido | (general) | 1, 8, 10, 12, 13 |
| 15 | `services/worker/src/worker/report_pdf.py` | Modify | Identificação "planejamento rápido", CNAE, faixa do Simples, origem PDF × digitado | (general) | 11, 14 |
| 16 | `services/worker/tests/test_declaracao_faturamento.py` | Create | Parser, validações, classificação, CNPJ | (general) | 6, 7 |
| 17 | `services/worker/tests/test_quick_view.py` | Create | Snapshot sintético, atividades ST/monofásico, digitação × PDF, RBT12 da declaração | (general) | 8 |
| 18 | `services/worker/tests/test_cnae.py` | Create | Prefixo mais longo, 4744-0/01 → Anexo I, CNAE fora da tabela, vedado | (general) | 4 |
| 19 | `services/worker/tests/test_cnpj_lookup.py` | Create | Cliente MCP com transporte simulado: sucesso, timeout, sem CNAE, descarte de sócios | (general) | 13 |
| 20 | `services/worker/tests/test_rapido_pipeline.py` | Create | Integração com banco: upload/digitação → homologação → premissas → projeção 2027 (3 regimes, ≤ 60 s) → aprovação → PDF | (general) | 14, 15 |
| 21 | `services/worker/tests/golden/rapido_2027.json`, `tests/test_decisao_golden.py`, `tests/conftest.py` | Create / Modify | Golden aprovado; amostra `RBT12.pdf`; fixtures do dossiê rápido | (general) | 17, 20 |
| 22 | `apps/web/src/lib/database.types.ts`, `lib/format.ts`, `lib/schemas.ts`, `lib/schemas.test.ts` | Modify | Tipos; rótulos (`DECLARACAO_FATURAMENTO`, `rapido`, faixa); schemas de digitação, CNAE e tipo do dossiê | (general) | 1 |
| 23 | `apps/web/src/app/(app)/cases/new/page.tsx`, `cases/actions.ts` | Modify | Escolher o tipo do dossiê (completo/rápido) na criação | (general) | 22 |
| 24 | `apps/web/src/app/(app)/cases/[id]/page.tsx`, `apps/web/src/components/ManualValuesForm.tsx`, `apps/web/src/components/CompanyCnae.tsx` | Modify / Create | Checklist do rápido (12 meses, folha, DRE), formulário de digitação, consulta/digitação de CNAE | (general) | 22 |
| 25 | `apps/web/src/app/(app)/cases/[id]/planning/page.tsx`, `planning/projection/[projId]/page.tsx`, `apps/web/src/components/SimplesBandTable.tsx` | Modify / Create | Só "Projetar 2027" no rápido; tabela de faixa do Simples | (general) | 22 |
| 26 | `scripts/verify.mjs`, `README.md`, `kb/simples-nacional/concepts/*` | Modify | Amostra `RBT12.pdf` no Verify Gate; seção do ciclo 5; KB da tabela CNAE → anexo | (general) | 21 |

**Total Files:** 26

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1–26 | Mesmo padrão dos ciclos 1–4 (build direto pelo agente principal) |

**Agent Discovery:** Not available

---

## Code Patterns

### Pattern 1: Adaptador do snapshot rápido

```python
def quick_view(content: dict, confirmed: Assumptions, cnae: CnaeTable, params: DecisionParams) -> SnapshotView:
    """Snapshot homologado do dossiê rápido → conteúdo no formato do dossiê completo (motor inalterado)."""
    months = faturamento_por_mes(content)            # 12 meses (PDF ou digitação), "AAAA-MM" → Decimal
    realized = [m for m in months if tem_folha(content, m) and tem_dre(content, m)]
    if not realized:
        raise ProjectionError("dossiê rápido sem mês com folha e DRE")
    values = []
    for m in realized:
        values += _synthetic_month(m, REALIZADO, fatos_do_mes(content, m, months[m]),
                                   atividades_sinteticas(content, confirmed, cnae),
                                   rba(months, m), rbaa(months, m), rbt12(months, m), serie_anterior(months, m))
    files = [dict(id="rapido-" + doc + "-" + m, doc_type=doc, competence=m + "-01", parser_version="rapido-1")
             for m in realized for doc in DOCS]
    return SnapshotView(dict(schema_version=1, company=content["company"], files=files, values=values))
```

### Pattern 2: Chamada MCP da consulta de CNPJ

```python
HEADERS = dict([("Content-Type", "application/json"), ("Accept", "application/json, text/event-stream")])


def rpc(method: str, params: dict | None = None, id_: int | None = None) -> dict:
    msg = dict(jsonrpc="2.0", method=method)
    if params is not None:
        msg["params"] = params
    if id_ is not None:
        msg["id"] = id_
    return msg


def consultar_cnpj(url: str, cnpj: str, client: httpx.Client) -> dict:
    """Só CNAE e razão social saem desta função; sócios e demais campos são descartados."""
    headers = dict(HEADERS)
    init = client.post(url, headers=headers, json=rpc("initialize", dict(
        protocolVersion="2025-03-26", capabilities=dict(), clientInfo=dict(name="planejamento-trib", version="1")), 1))
    headers["Mcp-Session-Id"] = init.headers["Mcp-Session-Id"]
    client.post(url, headers=headers, json=rpc("notifications/initialized"))
    resp = client.post(url, headers=headers, json=rpc("tools/call", dict(
        name="Consultar_CNPJ", arguments=dict(cnpj=cnpj)), 2))
    payload = json.loads(sse_json(resp.text)["result"]["content"][0]["text"])   # última linha "data:" do SSE
    return dict(
        razao_social=payload.get("razao_social"),
        cnae_principal=str(payload["cnae_fiscal"]),
        cnae_descricao=payload.get("cnae_fiscal_descricao"),
        cnaes_secundarios=[dict(codigo=str(c["codigo"]), descricao=c.get("descricao"))
                           for c in payload.get("cnaes_secundarios") or [] if c.get("codigo")],
    )
```

### Pattern 3: Digitação recusada quando há PDF

```sql
if exists (select 1 from public.source_files f
            where f.case_id = p_case_id and f.status = 'extracted'
              and (f.doc_type = p_doc_type or (p_doc_type = 'FATURAMENTO' and f.doc_type = 'DECLARACAO_FATURAMENTO'))
              and (p_doc_type = 'FATURAMENTO' or f.competence = p_competence)) then
  raise exception 'Mês com PDF extraído: altere o valor por ajuste justificado' using errcode = 'P0001';
end if;
```

---

## Data Flow

```text
1. Analista cria dossiê kind='rapido' (empresa + período de 12 meses)
   │
   ▼
2. "Consultar CNAE" → request_company_lookup → job lookup_company → MCP Consultar_CNPJ
   │   sucesso: companies.cnae_* (sem sócios) · falha/timeout: status 'falhou' → set_company_cnae (digitado)
   ▼
3. Upload da Declaração de Faturamento / folha / DRE → job extract → parser → validações
   │   ou digitação → enter_manual_values (recusa mês com PDF)
   ▼
4. homologate_case (rápido): 12 meses consecutivos, ≥ 1 folha, ≥ 1 DRE, validação da declaração ok,
   │   CNAE informado → snapshot (arquivos + valores + digitação) com hash; sem reconcile
   ▼
5. request_planning → suggest: quick_view (percentuais padrão) + tabela CNAE → premissas rapido.*,
   │   atividade.perfil por CNAE, ICMS proxy, outras receitas, premissas de 2027
   ▼
6. Analista confirma premissas → request_projection(case, 2027)
   │
   ▼
7. project: quick_view (premissas confirmadas) → build_projection (2026) → shift_year (2027)
   │   → calculate(regimes = SIMPLES, SIMPLES_HIBRIDO, PRESUMIDO) → sensibilidade → recomendação
   │   pendências → recomendação bloqueada (prévia)
   ▼
8. projections/projection_lines (inclui linhas 'faixa') → aprovação do RT → emit_report → PDF "planejamento rápido"
```

---

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| Automação n8n (MCP Server Trigger, `Consultar_CNPJ`, BrasilAPI) | MCP sobre HTTP/SSE (JSON-RPC) | Nenhuma (endpoint aberto) | out | Timeout 20 s; retry da fila até `WORKER_MAX_ATTEMPTS`; esgotado → status `falhou` e CNAE digitado |
| Supabase Storage | REST (existente) | Service role no worker | in/out | Igual aos ciclos anteriores |

---

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Parser e validações da declaração (AT-501–AT-503) | `services/worker/tests/test_declaracao_faturamento.py` | pytest | 12 meses, total 3.719.883,51, falha com soma adulterada, CNPJ divergente |
| Unit | Tabela CNAE (AT-510, AT-511) | `services/worker/tests/test_cnae.py` | pytest | 4744-0/01 → Anexo I; fora da tabela → sem sugestão |
| Unit | Cliente MCP (AT-508, AT-509) | `services/worker/tests/test_cnpj_lookup.py` | pytest + `httpx.MockTransport` | CNAE extraído, sócios descartados, timeout tratado |
| Unit | Snapshot sintético, faixa, sem Real (AT-512–AT-515) | `services/worker/tests/test_quick_view.py` | pytest | 3 regimes; linha `faixa` por mês; bloqueio com premissas pendentes; RBT12 > 4,8 mi → Simples inelegível |
| Integration | Fluxo completo, digitação, bloqueios, ≤ 60 s, PDF (AT-504–AT-507, AT-516, AT-517) | `services/worker/tests/test_rapido_pipeline.py`, `supabase/tests/planejamento_rapido.test.sql` | pytest `-m db`, pgTAP | fluxo verde; projeção ≤ 60 s; PDF com "planejamento rápido" |
| Golden | AT-518, AT-519 | `services/worker/tests/test_decisao_golden.py` | pytest | golden rápido aprovado + 4 goldens anteriores exatos |
| E2E / Verify Gate | Tudo | `scripts/verify.mjs` | `npm run verify` | exit 0 |

---

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Declaração com layout diferente | Âncoras ausentes | `LayoutNotRecognized` → arquivo `failed` | No | `file.failed` com código |
| Soma ≠ Total Geral | Validação `faturamento.soma_igual_total` | Bloqueia homologação até ajuste justificado | No | validação no snapshot |
| CNPJ divergente | Classificação × empresa | Arquivo `cnpj_mismatch` | No | `file.cnpj_mismatch` |
| Automação n8n fora/timeout | `httpx` timeout/HTTP ≠ 200/erro JSON-RPC | Retry da fila; esgotado → `cnae_lookup_status = 'falhou'` e formulário de digitação | Yes | `company.lookup_failed` (só IDs) |
| Resposta sem CNAE | `cnae_fiscal` ausente | Status `falhou` com motivo "sem CNAE" | No | `company.lookup_failed` |
| Digitação em mês com PDF | RPC | Recusa com mensagem de ajuste justificado | No | exceção P0001 |
| Premissa do rápido pendente | `blocking()` | Recomendação bloqueada (prévia) | No | `projection.blocked` |
| Soma de % ST + % monofásico > 1 | Confirmação da premissa | Recusa na RPC de confirmação | No | exceção P0001 |

---

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `CNPJ_LOOKUP_MCP_URL` | string | env do worker; sem padrão (consulta desativada se vazio) | No (endpoint aberto; tratar como interno) | Endereço MCP da automação n8n |
| `CNPJ_LOOKUP_TIMEOUT` | number (s) | env; padrão 20 | No | Timeout de cada chamada MCP |
| `services/worker/rules/cnae_anexos.json` | arquivo versionado | repositório | No | Tabela CNAE → anexo com versão/hash |

---

## Security Considerations

- `manual_values`: RLS por `is_member(office_id)`; escrita só pela RPC `enter_manual_values` (security definer, `auth.uid()` gravado como autor); imutável após homologação (mesmo gatilho do dossiê).
- Consulta de CNPJ: só o worker chama a automação; resposta da BrasilAPI contém sócios (dados pessoais) — descartada em memória, nunca gravada nem logada.
- Endpoint n8n sem autenticação: URL só em variável de ambiente do servidor; recomendação registrada de proteger com token antes de produção.
- `docs/Amostras/RBT12.pdf` tem CPF e CRC: fora do Git; golden `rapido_2027.json` só com valores, CNAE e códigos.
- RPCs novas com `revoke all ... from public, anon` e `grant execute ... to authenticated`, como nos ciclos anteriores.

---

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | Eventos JSON com IDs: `company.lookup_done`/`company.lookup_failed`, `file.extracted` (doc `DECLARACAO_FATURAMENTO`), `projection.done` com `kind` | Diagnostica consulta de CNAE, parser e projeção sem dados pessoais |
| Metrics | `duration_ms` e `engine_runs` da projeção (existentes) | Success Criteria ≤ 60 s |
| Tracing | N/A | Fluxo por jobs já rastreado por `job_id` |

---

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| AT-501, AT-502, AT-503 | Parser + validações (5–7) | `test_declaracao_faturamento.py` |
| AT-504, AT-507 | `homologate_case` do rápido (1) | pgTAP + `test_rapido_pipeline.py` |
| AT-505, AT-506 | `manual_values` + `enter_manual_values` (1, Decision 4) | pgTAP + `test_quick_view.py` |
| AT-508, AT-509 | `cnpj_lookup.py` + job (13, 14, Decision 5) | `test_cnpj_lookup.py` |
| AT-510, AT-511 | Tabela CNAE (3, 4, Decision 3) + premissas (10) | `test_cnae.py`, `test_quick_view.py` |
| AT-512, AT-514, AT-515 | `quick_view` + `regimes` (8, 12, Decisions 1, 6) | `test_quick_view.py` |
| AT-513 | Linha `faixa` (11, Decision 7) + telas/PDF (15, 25) | `test_quick_view.py`, `test_report_pdf.py` |
| AT-516, AT-517 | Pipeline + PDF (14, 15) | `test_rapido_pipeline.py` |
| AT-518 | Golden `rapido_2027.json` (21) | `test_decisao_golden.py` |
| AT-519 | Parâmetros opcionais com padrão atual (12) | goldens existentes + `npm run verify` |

---

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Tabela CNAE → anexo incompleta ou errada | Anexo sugerido errado | Sugestão pendente de confirmação; `verificado: false`; revisão contábil | Médio |
| Formato da resposta de `Consultar_CNPJ` diferente de A-501 | Consulta falha | Teste com transporte simulado + uma consulta real da amostra no Build, descartando sócios; fallback digitado | Baixo |
| Automação n8n aberta e dependente da BrasilAPI | Indisponibilidade ou abuso | Timeout, retry, fallback; token recomendado | Médio |
| ICMS proxy do DAS diferente do ICMS real | Presumido/Simples acima do sublimite distorcidos | Premissa confirmável; ressalva no PDF | Médio |
| Mudança em `simples.py` (linha informativa) afetar goldens | Regressão | Linhas informativas fora dos totais; goldens no Verify Gate | Baixo |

---

## Advisor Ledger

None — no formal external design review.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-26 | SDD Design by RDD | Initial version |

---

## Next Step

Execute o **SDD Build by RDD**.
