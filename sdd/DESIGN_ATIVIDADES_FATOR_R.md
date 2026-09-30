# DESIGN: Atividades mistas e Fator R no Planejamento Rápido

> Technical design for implementing Atividades mistas e Fator R no Planejamento Rápido

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | ATIVIDADES_FATOR_R |
| **Date** | 2026-09-28 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_ATIVIDADES_FATOR_R.md` |
| **DEFINE** | `sdd/DEFINE_ATIVIDADES_FATOR_R.md` |
| **UX REVIEW** | N/A |
| **LLM Prompts** | false |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
 Consulta CNPJ (n8n/BrasilAPI) ──► companies.cnaes_secundarios  (JÁ EXISTE: cnpj_lookup.parse_payload)
                                          │
 Tela do dossiê rápido ─ CaseActivities.tsx ─► saveActivities (server action) ─► rpc set_case_activities
                                          │                                            │
                                          ▼                                            ▼
                               rapido_blockers (soma = 100,00%)            public.case_activities (RLS, trava
                                          │                                  de homologado, cascade no delete)
                                          ▼
                               homologate_case ──► snapshot.content.activities[]
                                                            │
 Worker ────────────────────────────────────────────────────┼────────────────────────────────────────────
   quick_view.build_quick_case ◄────────────────────────────┘
     ├─ activity_templates: 1 atividade × variantes (normal/ST/mono) por CNAE marcado
     ├─ receita da atividade = faturamento × percentual (ST/mono saem das atividades de comércio)
     └─ fator_r.inject_folha_12m ──► premissas folha.folha_12m por competência (derivadas, não editáveis)
            ▲  fator_r.folha_timeline (salários + pró-labore + FGTS 8%, realizado + projetado)
            │  fator_r.json (versão/hash próprios, não verificado)
   simples.py (motor existente, sem mudança de regra) ──► linhas por atividade + linha "fator_r"
   fator_r.folha_ideal_lines ──► linhas informativas "folha_ideal_*" (fora dos totais)
                                          │
                                          ▼
   Tela de planejamento/projeção: ActivitiesTable, FatorRTable, FolhaIdealTable │ PDF: report_pdf.py
```

---

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| `case_activities` + RPC `set_case_activities` | Guardar CNAEs marcados e percentuais do dossiê rápido | Postgres, security definer, RLS `is_member`, trigger `tg_block_if_homologated` | case_id, lista de itens com cnae, descricao e percentual | linhas da tabela, audit `case_activities.set` | `tax_cases`, `write_audit` |
| `rapido_blockers` / `homologate_case` (redefinidos) | Bloquear soma ≠ 100,00% e levar atividades ao snapshot | plpgsql (cópia da versão de `20260928000006` + acréscimos) | case_id | bloqueios; `content.activities` | `case_activities` |
| `CaseActivities.tsx` + `saveActivities` | Marcar atividades, digitar percentuais, incluir CNAE manual | React client + server action + zod | CNAEs da empresa, atividades salvas | chamada RPC; redirect com erro/ok | `schemas.ts`, `actions.ts` |
| `quick_view.py` (modificado) | Montar atividades sintéticas por CNAE marcado e parcelas de receita | Python, formato do dossiê completo | `content.activities`, premissas confirmadas | `QuickCase` com N atividades | `fator_r.py`, `cnae.py` |
| `fator_r.py` (novo) | Linha do tempo da folha, folha 12m por competência, tratamento de meses sem folha, folha ideal | Python puro, Decimal | folhas mensais, RBT12, escolha, parâmetros | premissas derivadas; linhas informativas | `rules/fator_r.json`, `simples.band_rates` |
| `rules/fator_r.json` (novo) | Parâmetros FGTS 8%, INSS sócio 11%, provisões 13º/férias | JSON versionado com hash próprio | — | `FatorRParams` | `config.py` |
| `projection.py` (modificado) | Usar a folha 12m derivada nos meses projetados do Rápido | gancho opcional `folha_12m_override` | plano mensal projetado | premissas por competência | `fator_r.py` |
| `pipeline.py` (modificado) | Ligar injeção da folha 12m e linhas de folha ideal no cálculo/projeção do Rápido | worker existente | snapshot rápido | cálculo/projeção com linhas novas | `quick_view.py`, `fator_r.py` |
| `ActivitiesTable`, `FatorRTable`, `FolhaIdealTable` | Quadros na tela | React server components | linhas do motor, snapshot | tabelas | `format.ts` |
| `report_pdf.py` (modificado) | Mesmos quadros no PDF | reportlab | `ReportData.lines`, snapshot | seções do PDF | — |

---

## Key Decisions

### Decision 1: Atividades em tabela própria, editadas antes da homologação

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-28 |
| **Source** | DEFINE (AT-603, AT-615) + padrão observado em `manual_values` |

**Context:** O DEFINE exige que a soma ≠ 100% bloqueie a homologação e que atividades fiquem travadas no dossiê homologado.

**Choice:** Tabela `public.case_activities (id, office_id, case_id, cnae char(7), descricao, percentual numeric(7,4), origem 'receita'|'manual')`, FK `(case_id, office_id) → tax_cases on delete cascade`, trigger `tg_block_if_homologated`, só `select` direto; escrita pela RPC `set_case_activities(p_case_id, p_items jsonb)` que substitui o conjunto inteiro. `homologate_case` grava `content.activities`.

**Rationale:** Reusa exatamente o padrão de `manual_values` (trava, purge, RLS, snapshot); o motor lê o snapshot imutável.

**Alternatives Rejected:**
1. Premissa `rapido.atividades` na fase de planejamento — não bloqueia a homologação e fica editável depois dela, contrariando AT-603/AT-615.
2. Coluna jsonb em `tax_cases` — sem constraint por linha nem trilha de auditoria por item.

**Consequences:**
- Reabrir o dossiê libera a edição (fluxo `reopen_case` existente).
- Snapshot sem `activities` (dossiês antigos) ou dossiê sem linhas salvas = CNAE principal com 100% (retrocompatível; AT-605 e golden `rapido_2027`). AT-604 é aplicado na gravação: lista vazia é recusada pela RPC.

### Decision 2: ICMS-ST e monofásico continuam percentuais da empresa, retirados das atividades de comércio

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-28 |
| **Source** | DEFINE AT-614 + Brainstorm decisão 8 |

**Context:** No ciclo 5 os percentuais ST/mono dividem a receita da única atividade em variantes normal/ST/mono.

**Choice:** `pct_icms_st` e `pct_monofasico` continuam frações da receita total; a receita ST/mono é distribuída proporcionalmente entre as atividades cujo perfil confirmado é Anexo I ou II. Se `st + mono` > parcela de comércio → `QuickCaseError` com mensagem. Atividades não comerciais só têm a variante normal com receita.

**Rationale:** Com uma atividade de comércio o resultado é idêntico ao ciclo 5; evita zerar PIS/Cofins de serviço por engano.

**Alternatives Rejected:**
1. Mesma fração aplicada a todas as atividades — zeraria PIS/Cofins/ICMS de serviços.
2. Percentual ST/mono por atividade — fora de escopo (DEFINE).

**Consequences:**
- Dossiê antigo com atividade única de serviço e ST > 0 passa a falhar com mensagem clara (caso inexistente nos goldens).

### Decision 3: Folha 12m do Rápido é derivada, não premissa editável

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-28 |
| **Source** | DEFINE AT-607–AT-610 + código (`quick_view.py:198-208`, `projection.py:222-250`) |

**Context:** Hoje a folha 12m é sugestão igual para todos os meses (média × 12) e, na projeção, a média das competências realizadas.

**Choice:** `fator_r.folha_timeline` monta a folha por mês (salários + pró-labore + FGTS 8% sobre salários) das competências realizadas e projetadas; `inject_folha_12m` grava `folha.folha_12m` por competência = soma dos 12 meses anteriores, com origem contendo rbt12, meses_informados e tratamento. Meses sem folha seguem a premissa de caso `rapido.folha_incompleta` (`media` | `zero`). A sugestão antiga é removida de `rapido_suggestions`; a nova sugestão `rapido.folha_incompleta` só aparece quando algum mês da janela não tem folha, com valor `None` (obriga escolha) e escolhas `["media","zero"]` (apenas `["zero"]` sem nenhum mês de folha). Na projeção, `projection.py` recebe `folha_12m_override` do pipeline para o Rápido.

**Rationale:** Fator R correto por competência sem mudar a regra do motor (`simples.py` continua lendo `folha.folha_12m`).

**Alternatives Rejected:**
1. Mudar `assumptions.py`/`simples.py` para todos os dossiês — altera o dossiê completo (fora de escopo) e os goldens `motor_*`/`decisao_*`.
2. Manter a folha 12m editável — permitiria voltar ao número errado sem rastreio.

**Consequences:**
- O dossiê completo não muda.
- Folha antes da declaração (meses sem dado) sempre depende da escolha registrada, visível no PDF.

### Decision 4: Parâmetros da folha ideal em `rules/fator_r.json` com hash próprio

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-28 |
| **Source** | Constraint do DEFINE (alíquotas configuráveis, não verificadas) + padrão `cnae_anexos.json` |

**Context:** Os goldens registram o hash das regras do exercício (2026 `e00eaa79e1ae`, 2027.1.0 `e60103aefe5e`); alterar `encargos.json` mudaria os hashes.

**Choice:** Arquivo `services/worker/rules/fator_r.json` (`versao`, `verificado: false`, `fgts: 0.08`, `inss_socio: 0.11`, `provisoes_salario: 0.1944`) carregado como a tabela CNAE, com hash exibido na origem das linhas.

**Rationale:** Parâmetros configuráveis sem tocar no manifest das regras nem nos goldens.

**Alternatives Rejected:**
1. Chaves novas em `encargos.json` — muda o hash das regras e invalida goldens.
2. Constantes no código — não configuráveis.

**Consequences:**
- Um arquivo de regra a mais a revisar com a contabilidade.

### Decision 5: Folha ideal como linhas informativas geradas depois do cálculo

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-28 |
| **Source** | DEFINE AT-611 + padrão `kind="informativo"` (`memory.py:57`) |

**Context:** A simulação não pode entrar nos totais nem alterar `simples.py`.

**Choice:** `fator_r.folha_ideal_lines(lines, qc, params, rules)` percorre as linhas `fator_r` com resultado Anexo V e gera, por competência e atividade, linhas `kind="informativo"`: `folha_ideal_faltante` (0,28 × RBT12 − folha 12m), `folha_ideal_economia` (Simples da atividade no V − no III, pela `band_rates`), `folha_ideal_prolabore` (custo = faltante × 11%) e `folha_ideal_salario` (salário = faltante ÷ 1,08; custo = salário × (1 + 8% + provisões)). O pipeline anexa essas linhas no cálculo e na projeção do Rápido.

**Rationale:** Não mexe no motor; aproveita a exclusão de informativos dos totais e a persistência de linhas existente.

**Alternatives Rejected:**
1. Calcular na tela (TypeScript) — duplicaria regras do Simples fora do worker e ficaria fora do PDF.

**Consequences:**
- A economia usa a receita da atividade no mês × diferença de alíquota efetiva; aproximação documentada na origem da linha.

---

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `supabase/migrations/20260929000008_atividades_fator_r.sql` | Create | `case_activities`, RLS, trigger, `set_case_activities`, `rapido_blockers` e `homologate_case` redefinidos com `activities` | (general) | None |
| 2 | `supabase/tests/atividades_fator_r.test.sql` | Create | pgTAP: soma ≠ 100 bloqueia, lista vazia/CNAE inválido recusados, trava pós-homologação, RLS entre escritórios, snapshot com `activities` | (general) | 1 |
| 3 | `apps/web/src/lib/database.types.ts` | Modify | Regerar (`npm run db:types`) | (general) | 1 |
| 4 | `services/worker/rules/fator_r.json` | Create | Parâmetros FGTS/INSS sócio/provisões, versão e `verificado: false` | (general) | None |
| 5 | `services/worker/src/worker/config.py` | Modify | `fator_r_params_path(settings)` como `cnae_table_path` | (general) | 4 |
| 6 | `services/worker/src/worker/engine/fator_r.py` | Create | `load_fator_r_params`, `folha_timeline`, `inject_folha_12m`, `folha_ideal_lines`, `FolhaIncompletaError` | (general) | 4 |
| 7 | `services/worker/src/worker/engine/quick_view.py` | Modify | Atividades por CNAE marcado, parcelas de receita, ST/mono nas atividades de comércio, sugestões por atividade, `rapido.folha_incompleta`, remoção da sugestão média × 12 | (general) | 6 |
| 8 | `services/worker/src/worker/engine/projection.py` | Modify | Parâmetro opcional `folha_12m_override` para meses projetados | (general) | 6 |
| 9 | `services/worker/src/worker/pipeline.py` | Modify | Rápido: injeção da folha 12m e linhas de folha ideal no cálculo e na projeção | (general) | 7, 8 |
| 10 | `services/worker/src/worker/report_pdf.py` | Modify | Seções "Atividades", "Fator R mês a mês" (com tratamento de folha incompleta) e "Folha ideal" | (general) | 9 |
| 11 | `services/worker/tests/test_fator_r.py` | Create | Unit: linha do tempo com FGTS, janela de 12 meses, média × zero, sem folha, folha ideal | (general) | 6 |
| 12 | `services/worker/tests/test_quick_view.py` | Modify | N atividades, percentuais, ST/mono em comércio, snapshot antigo = principal 100% | (general) | 7 |
| 13 | `services/worker/tests/golden/rapido_misto_2027.json` | Create | Golden fictício comércio (I) + serviço Fator R (III/V) com mudança de anexo — aprovado pelo usuário | (general) | 9 |
| 14 | `services/worker/tests/test_rapido_pipeline.py` | Modify | Golden `rapido_misto_2027`, não regressão `rapido_2027`, parada sem escolha de folha incompleta | (general) | 9, 13 |
| 15 | `apps/web/src/lib/schemas.ts` | Modify | zod `activitiesSchema` (CNAE 7 dígitos, percentual 0–100 com 2 casas, soma exata 100,00) | (general) | None |
| 16 | `apps/web/src/lib/schemas.test.ts` | Modify | Casos da soma exata, CNAE inválido, lista vazia | (general) | 15 |
| 17 | `apps/web/src/app/(app)/cases/actions.ts` | Modify | Server action `saveActivities` → rpc `set_case_activities` | (general) | 3, 15 |
| 18 | `apps/web/src/components/CaseActivities.tsx` | Create | Formulário de atividades (CNAEs da Receita + manual, percentuais, soma ao vivo) | (general) | 17 |
| 19 | `apps/web/src/app/(app)/cases/[id]/page.tsx` | Modify | Seção "Atividades da empresa" no dossiê rápido (editável antes da homologação, leitura depois) | (general) | 18 |
| 20 | `apps/web/src/components/FatorRTable.tsx` | Create | Quadro Fator R mês a mês a partir das linhas `fator_r` | (general) | 9 |
| 21 | `apps/web/src/components/FolhaIdealTable.tsx` | Create | Bloco folha ideal: pró-labore × salário lado a lado | (general) | 9 |
| 22 | `apps/web/src/app/(app)/cases/[id]/planning/projection/[projId]/page.tsx` | Modify | Renderizar quadro de atividades, `FatorRTable` e `FolhaIdealTable` | (general) | 20, 21 |
| 23 | `apps/web/src/lib/format.ts` | Modify | Rótulos das linhas novas e de `rapido.folha_incompleta` | (general) | None |

**Total Files:** 23

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1–23 | Sem catálogo de agentes no projeto; builds anteriores foram executados no contexto principal |

**Agent Discovery:** Not available

---

## Code Patterns

### Pattern 1: RPC de gravação com trava e soma exata

```sql
create or replace function public.set_case_activities(p_case_id uuid, p_items jsonb)
returns void language plpgsql security definer set search_path = public as $$
declare
  v public.tax_cases;
  v_total numeric;
begin
  select * into v from public.tax_cases where id = p_case_id;
  if v.id is null or not public.is_member(v.office_id) then
    raise exception 'Dossiê não encontrado' using errcode = '42501';
  end if;
  if v.kind <> 'rapido' then raise exception 'Atividades só no planejamento rápido' using errcode = 'P0001'; end if;
  if jsonb_array_length(coalesce(p_items, '[]')) = 0 then
    raise exception 'Marque ao menos uma atividade' using errcode = 'P0001';
  end if;
  if exists (select 1 from jsonb_array_elements(p_items) i where i->>'cnae' !~ '^[0-9][0-9][0-9][0-9][0-9][0-9][0-9]$') then
    raise exception 'CNAE inválido (7 dígitos)' using errcode = 'P0001';
  end if;
  select sum((i->>'percentual')::numeric) into v_total from jsonb_array_elements(p_items) i;
  if jsonb_array_length(p_items) > 1 and v_total <> 100 then
    raise exception 'A soma dos percentuais é %%, precisa ser 100,00%%', v_total using errcode = 'P0001';
  end if;
  delete from public.case_activities where case_id = p_case_id;   -- trigger bloqueia se homologado
  insert into public.case_activities (office_id, case_id, cnae, descricao, percentual, origem)
  select v.office_id, p_case_id, i->>'cnae', nullif(trim(i->>'descricao'), ''),
         case when jsonb_array_length(p_items) = 1 then 100 else (i->>'percentual')::numeric end,
         coalesce(i->>'origem', 'manual')
    from jsonb_array_elements(p_items) i;
  perform public.write_audit(v.office_id, 'case_activities.set', 'tax_cases', p_case_id, null,
    jsonb_build_object('cnaes', (select jsonb_agg(i->>'cnae') from jsonb_array_elements(p_items) i)));
end $$;
```

### Pattern 2: Folha 12m derivada por competência

```python
@dataclass(frozen=True)
class FatorRParams:
    version: str
    hash: str
    verified: bool
    fgts: Decimal
    inss_socio: Decimal
    provisoes_salario: Decimal


class FolhaIncompletaError(Exception):
    """Fator R: escolha como tratar os meses sem folha."""


def folha_12m(comp: str, timeline: dict[str, Decimal | None], tratamento: str | None) -> tuple[Decimal, dict]:
    months = previous_months(comp, 12)
    known = [timeline[m] for m in months if timeline.get(m) is not None]
    missing = 12 - len(known)
    if missing and tratamento not in ("media", "zero"):
        raise FolhaIncompletaError("Fator R: escolha como tratar os meses sem folha")
    if missing and tratamento == "media" and not known:
        raise FolhaIncompletaError("Fator R: sem nenhum mês de folha, só é possível considerar zero")
    fill = (sum(known, ZERO) / len(known)) if (missing and tratamento == "media") else ZERO
    total = sum(known, ZERO) + fill * missing
    return money(total), {"source": "rapido_fator_r", "meses_informados": len(known),
                          "tratamento": tratamento if missing else None}
```

### Pattern 3: Linha informativa de folha ideal

```python
Line("SIMPLES", comp, "folha_ideal_prolabore", money(faltante), params.inss_socio, money(faltante * params.inss_socio),
     "pró-labore adicional " + brl(faltante) + " × INSS " + pct(params.inss_socio, 2), dict(tabela="fator_r", versao=params.version),
     kind="informativo", activity=act_key, verified=params.verified,
     origin=dict(economia=str(money(economia)), faltante=str(money(faltante))))
```

---

## Data Flow

```text
1. Consulta CNPJ (existente) → companies.cnae_principal + cnaes_secundarios (código/descrição; sem QSA)
   │
   ▼
2. Tela do dossiê rápido → CaseActivities: marca CNAEs, percentuais, CNAE manual → zod → rpc set_case_activities
   │  falha: soma ≠ 100 / vazio / CNAE inválido → redirect com erro; homologado → erro do trigger
   ▼
3. homologate_case → rapido_blockers (soma = 100,00% quando há linhas) → snapshot.content.activities[]
   │
   ▼
4. Worker (sugestões) → build_quick_case: atividades sintéticas por CNAE × variantes; perfil sugerido por CNAE;
   │  sugestão rapido.folha_incompleta quando faltar folha na janela
   ▼
5. Cálculo → build_quick_case(confirmed) → inject_folha_12m (FolhaIncompletaError se sem escolha) → motor
   │  (simples/presumido por atividade) → folha_ideal_lines → linhas persistidas
   ▼
6. Projeção 2026/2027 → projection(..., folha_12m_override=timeline projetada) → mesmas etapas 5
   │
   ▼
7. Tela (ActivitiesTable, FatorRTable, FolhaIdealTable) e PDF (report_pdf) a partir das linhas e do snapshot
```

---

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| n8n MCP `Consultar_CNPJ` (BrasilAPI) | MCP JSON-RPC sobre HTTP (existente, sem mudança) | Nenhuma (pendência conhecida) | out | Falha → status `falhou`; tela usa só o CNAE principal/manual; sem retry automático novo |
| Supabase Postgres | RPC + RLS | Sessão do usuário (web) / service role (worker) | bidirectional | Erro de RPC → mensagem na tela; worker marca job com erro |

---

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Folha com FGTS, janela 12m, média/zero, sem folha, folha ideal (AT-607–AT-611) | `services/worker/tests/test_fator_r.py` | pytest | todos passam |
| Unit | Atividades, parcelas, ST/mono em comércio, CNAE fora da tabela, retrocompatibilidade (AT-605, AT-606, AT-612, AT-614) | `services/worker/tests/test_quick_view.py` | pytest | todos passam |
| Integration | Golden `rapido_misto_2027` + não regressão `rapido_2027` + parada sem escolha (AT-608, AT-613) | `services/worker/tests/test_rapido_pipeline.py` | pytest + Postgres local | diferença R$ 0,00 |
| Integration | RPC, bloqueios, trava, RLS, snapshot (AT-602–AT-604, AT-615, AT-617) | `supabase/tests/atividades_fator_r.test.sql` | pgTAP | `Result: PASS` |
| Unit | zod da soma exata e CNAE (AT-603/604 na UI) | `apps/web/src/lib/schemas.test.ts` | vitest | todos passam |
| E2E / Verify Gate | Suíte completa + goldens existentes | `npm run verify` | pytest + pgTAP + tsc + vitest | exit 0 |
| Smoke (complementar) | Dossiê rápido fictício com 2 atividades pela tela; quadros visíveis (AT-616) | navegador interno em localhost | manual assistido | quadros renderizados |

---

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Soma ≠ 100,00% / lista vazia / CNAE inválido | zod + RPC | Mensagem na tela; nada gravado | No | audit só em sucesso |
| Edição após homologação | `tg_block_if_homologated` | Erro "reabra o dossiê" | No | — |
| Folha incompleta sem escolha | `FolhaIncompletaError` | Job de cálculo falha com a mensagem do AT-608 exibida na tela de planejamento | No | log com case_id e código |
| ST + mono > parcela de comércio | `QuickCaseError` | Mensagem pedindo ajuste dos percentuais | No | log com case_id |
| CNAE fora da tabela | `cnae.match` = None | Perfil sem sugestão; cálculo bloqueado até escolha (comportamento existente) | No | — |
| Consulta CNPJ indisponível | status `falhou` (existente) | Usuário inclui CNAE manual | Manual | log existente |

---

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `fator_r.json:fgts` | decimal | `0.08` | No | FGTS sobre salários (folha do Fator R e custo do salário) |
| `fator_r.json:inss_socio` | decimal | `0.11` | No | INSS do sócio sobre pró-labore adicional |
| `fator_r.json:provisoes_salario` | decimal | `0.1944` | No | 13º (1/12) + férias com 1/3 (1/12 × 4/3) |
| `fator_r.json:verificado` | boolean | `false` | No | Linhas mostram "não verificado" |
| `rapido.folha_incompleta` | premissa de caso | sem default (`media` / `zero`) | No | Tratamento dos meses sem folha |

---

## Security Considerations

- `case_activities` só com `select` via RLS `is_member(office_id)`; escrita apenas pela RPC security definer que confere `is_member` e `kind = 'rapido'` (AT-617 em pgTAP).
- Descrição do CNAE é texto livre curto: `trim`, limite de 300 caracteres na RPC e no zod; renderização React escapa HTML.
- Nenhum dado de sócios/QSA é lido ou gravado; `cnpj_lookup.parse_payload` continua descartando.
- Logs do worker só com IDs e códigos (case_id, códigos de erro), nunca valores de folha.
- Golden novo totalmente fictício (CNPJ e razão social de exemplo), sem PII.

---

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | Worker: `case_id`, job id e código (`FOLHA_INCOMPLETA`, `ST_MONO_EXCEDE_COMERCIO`) | Diagnóstico de cálculo bloqueado |
| Metrics | N/A (sem stack de métricas no projeto) | — |
| Tracing | Audit `case_activities.set` com CNAEs | Quem alterou as atividades |

---

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| AT-601 | `cnpj_lookup.parse_payload` e coluna `cnaes_secundarios` já existentes (sem mudança) | `test_cnpj_lookup.py` existente |
| AT-602, AT-605 | Decision 1, manifest 1, 17, 18 | pgTAP 2, vitest 16 |
| AT-603, AT-604 | RPC + `rapido_blockers` (manifest 1), zod (15) | pgTAP 2, vitest 16 |
| AT-606 | Decision 1/2, manifest 7 | pytest 12 |
| AT-607 | Decision 3, manifest 6, 7, 8, 9 | pytest 11, 14 |
| AT-608, AT-609, AT-610 | Decision 3, Pattern 2 | pytest 11, 14 |
| AT-611 | Decision 5, Pattern 3 | pytest 11, golden 13 |
| AT-612 | comportamento existente de perfil sem sugestão, manifest 7 | pytest 12 |
| AT-613 | Decisions 3/4 (motor e hashes intocados) | goldens existentes em `npm run verify` |
| AT-614 | Decision 2 | pytest 12, golden `rapido_2027` |
| AT-615 | trigger `tg_block_if_homologated` | pgTAP 2 |
| AT-616 | manifest 10, 19–22 | smoke no navegador + `test_report_pdf.py` |
| AT-617 | RLS + RPC | pgTAP 2 |

---

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Chaves de atividade mudarem e quebrarem `rapido_2027` | Golden diverge | Chave por CNAE com a mesma função `slug` atual; teste de não regressão | Baixo |
| Redefinir `homologate_case` perder comportamento do ciclo 5/gestão | Homologação quebrada | Copiar a versão de `20260928000006` e só acrescentar; pgTAP existentes | Baixo |
| Economia da folha ideal ser aproximação | Decisão com número aproximado | Origem da linha explica a fórmula; bloco marcado "informativo / não verificado" | Médio |
| Parâmetros de provisões não revisados pela contabilidade | Custo do salário impreciso | `verificado: false`, configurável | Médio |

---

## Advisor Ledger

None — no formal external design review.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-28 | SDD Design by RDD | Initial version |

---

## Next Step

Execute o **SDD Build by RDD**.
