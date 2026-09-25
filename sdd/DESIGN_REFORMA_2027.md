# DESIGN: Reforma Tributária 2027 (ciclo 4 do Planejamento Tributário)

> Technical design for implementing Reforma Tributária 2027 — regras 2027 versionadas, motor por exercício com CBS/IBS, Simples por dentro × híbrido, projeção 2027 e importação do Livro de Apuração do ICMS.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | REFORMA_2027 |
| **Date** | 2026-09-25 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_REFORMA_2027.md` |
| **DEFINE** | `sdd/DEFINE_REFORMA_2027.md` |
| **UX REVIEW** | N/A |
| **LLM Prompts** | false |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
 Upload (ciclo 1)                         Worker Python
 Livro de Apuração ICMS ──▶ classify ──▶ parser LIVRO_ICMS_ALTERDATA ──▶ validações de soma
 (PDF, antes da homologação)                                   │
                                                               ▼
                                     reconcile: R1–R6 + R7 (compras CFOP × conta 13101)
                                                               │  homologação (snapshot)
                                                               ▼
 suggest(): premissas grp "reforma_2027" (alíquotas CBS/IBS sem padrão, crescimento 0%,
            base de créditos por mês ← livro ou conta 13101)
                                                               │
 request_projection(case, 2027) ──▶ job project ──────────────┘
          │
          ▼
 Projetor 2026 (ciclo 3) ──▶ deslocar_para(2027, crescimento) ──▶ SnapshotView sintética 2027
                                                                   │
 rules/2026 (2026.1.0, intacta)          rules/2027 (2027.1.0) ────┤
                                                                   ▼
            Motor por exercício: SIMPLES (por dentro) · SIMPLES_HIBRIDO · PRESUMIDO · REAL
            (CBS/IBS no lugar de PIS/Cofins; crédito financeiro; IPI zero)
                                                                   ▼
            Sensibilidade (6 variáveis: ciclo 3 + alíquota da CBS) ─▶ Recomendação (4 alternativas)
                                                                   ▼
            projections / recommendations (ciclo 3) ─▶ fluxo de aprovação ─▶ PDF "exercício 2027"
```

---

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| Regras 2027 | Nova versão por exercício: cópia das regras de 2026 vigentes em 2027 + consumo CBS/IBS + Simples 2027 com opção híbrida | JSON versionado (`rules/2027/`, versão 2027.1.0) | — | `RuleSet` 2027 com `consumo` | Rules Loader (ciclo 2) |
| Política de decisão 2027 | Variáveis da sensibilidade (6, com alíquota da CBS), ressalvas de 2027 | `rules/decisao_2027.json` (versão 2027.1.0, hash próprio) | — | `DecisionParams` 2027 | Loader do ciclo 3 |
| Parser do Livro de Apuração | Entradas/saídas por CFOP (valor contábil, base, imposto, isentas, outras), subtotais e totais, com página | Parser por coordenadas (padrão ciclo 1) | PDF | `ParseResult` `LIVRO_ICMS_ALTERDATA` | classify, validations |
| Conciliação R7 | Compras para comercialização (CFOP 1102, 2102, 1403, 2403) × débitos da conta mapeada `compras_mercadorias` (13101) | `reconcile.py` (padrão R1–R6) | Fatos do livro e do balancete | `ReconciliationResult` R7 | Mapeamentos do escritório |
| Premissas de 2027 | Alíquotas de CBS e IBS (sem padrão), crescimento (0%), base de créditos por mês (livro ou 13101) | `assumptions.suggest()` (grupo `reforma_2027`) | Snapshot | Sugestões com origem | Parser do livro |
| Motor CBS/IBS | Débito = receita × alíquota; crédito = base de créditos × alíquota; saldo credor transportado | `engine/cbs_ibs.py` (funções puras) | Receita, base de créditos, premissas | Linhas de memória | Regras 2027 |
| Motor por exercício | Presumido/Real/Simples chamam CBS/IBS quando `rules.consumo` existe; `SIMPLES_HIBRIDO` como quarta alternativa | Ajuste em `presumido.py`, `real.py`, `simples.py`, `calculate.py` | `SnapshotView`, premissas, `RuleSet` | `SimulationResult` com 3 ou 4 regimes | Motor CBS/IBS |
| Projeção 2027 | Desloca a Projeção 2026 para 2027 com crescimento; premissas por mês escaladas | `engine/projection.py` (`shift_year`) | `ProjectedCase` 2026 | `ProjectedCase` 2027 | Projetor ciclo 3 |
| Orquestração por exercício | `project(year)` escolhe regras e política do exercício; bloqueia 2027 sem alíquotas | `engine/decision.py` | Snapshot, premissas, catálogo de regras | `ProjectionResult` | Projeção, motor, sensibilidade, recomendação |
| Banco | Tipo de documento novo, R7, alvo de mapeamento, regime `SIMPLES_HIBRIDO`, `request_projection(case, year)`, pendências por exercício | Migration + pgTAP | RPCs | Estados | Ciclos 1–3 |
| Telas | Botão "Projetar 2027", grupo de premissas de 2027, quatro alternativas no comparativo, R7 na conciliação, alvo de mapeamento no admin | Next.js 16 | Supabase | UI | Banco |

---

## Key Decisions

### Decision 1: Regras 2027 como versão completa e independente

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | Brainstorm (Approach A) + DEFINE (Constraints) + evidência (`load_rules(rules_dir, exercise)` já carrega por exercício) |

**Context:** O motor carrega regras por exercício (`services/worker/rules/<ano>/manifest.json`) e grava versão/hash em cada simulação; as regras de 2026 não podem mudar (goldens).

**Choice:** `services/worker/rules/2027/` com `manifest.json` (versão 2027.1.0, exercício 2027, vigência 01/01–31/12/2027) e os arquivos `simples.json`, `presumido.json`, `real.json`, `encargos.json`, `elegibilidade.json`, `atividades.json` copiados de 2026 com os ajustes de 2027, mais `consumo.json` novo:

| Arquivo | Ajuste de 2027 |
|---|---|
| `consumo.json` | Tributos `cbs` e `ibs`; alíquotas pelas premissas `reforma.cbs_aliquota` e `reforma.ibs_aliquota`; base = receita sem ICMS/ISS (LC 214, art. 12, § 2º, via fontes secundárias); crédito financeiro sobre a base de créditos; saldo credor transportado; CFOPs creditáveis (1102, 2102, 1403, 2403, 2353) e de devolução de venda (1202, 1411) |
| `simples.json` | Mesmos anexos e faixas; na repartição, as parcelas de `pis` + `cofins` passam a `cbs` e `ibs` recebe 0 em 2027 (A-401); `hibrido: true` |
| `presumido.json`, `real.json` | Sem PIS/Cofins (cumulativo e não cumulativo); IRPJ/CSLL, LC 224 e demais regras iguais a 2026 (A-403) |
| demais | Iguais a 2026 (A-403) |

Todos os arquivos de 2027 com `verificado: false` e `fonte` indicando LC 214/2025 via fontes secundárias.

**Rationale:** Isola 2027 por versão/hash, mantém 2026 intacto e segue o mecanismo de versionamento já existente.

**Alternatives Rejected:**
1. Flag de exercício dentro das regras de 2026 — mudaria o hash de 2026 e os goldens.
2. Regras de 2027 só com o delta — o loader carrega um exercício por vez; delta exigiria herança nova.

**Consequences:**
- Duplicação controlada dos arquivos que não mudam em 2027 (documentada no manifest).
- Correção futura da repartição do DAS = nova versão 2027.x.

### Decision 2: Motor por exercício com `rules.consumo` e quarta alternativa `SIMPLES_HIBRIDO`

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | DEFINE (AT-401 a AT-405) |

**Context:** O motor atual tem `REGIMES = ("SIMPLES", "PRESUMIDO", "REAL")` e PIS/Cofins embutidos em `presumido.month_pis_cofins`, `real.month_pis_cofins` e na repartição do Simples.

**Choice:**
- `RuleSet.consumo` (None em 2026). Em `presumido.py` e `real.py`, o cálculo mensal de PIS/Cofins é substituído por `cbs_ibs.month_lines(...)` quando `rules.consumo` existe; em 2026 o código atual roda sem alteração.
- `cbs_ibs.month_lines`: para cada tributo (`cbs`, `ibs`), débito = (receita − devoluções de venda) × alíquota, crédito = base de créditos × alíquota + saldo anterior, devido = máx(0, débito − crédito), saldo credor transportado (mesmo padrão do ciclo 2 para PIS/Cofins).
- Simples 2027 por dentro: `band_rates` usa a repartição de 2027 (`cbs` no lugar de `pis`/`cofins`).
- `SIMPLES_HIBRIDO`: mesmo cálculo do Simples com `cbs`/`ibs` excluídos do DAS + `cbs_ibs.month_lines` no regime regular; elegibilidade igual à do Simples.
- `regimes_for(rules)`: os três regimes + `SIMPLES_HIBRIDO` quando `rules.simples["hibrido"]`.

**Rationale:** Mudança localizada nos pontos onde PIS/Cofins aparecem; 2026 segue pelo mesmo caminho de código.

**Alternatives Rejected:**
1. Motor separado para 2027 — duplicaria faixas, limites e encargos (Approach C, rejeitada).
2. Híbrido como "cenário" do Simples em vez de regime — a recomendação e o ranking precisam tratá-lo como alternativa.

**Consequences:**
- Constraint `regime in (...)` de `simulation_lines` e `projection_lines` ganha `SIMPLES_HIBRIDO`.
- Telas e PDF passam a iterar a lista de regimes do resultado, não uma lista fixa.

### Decision 3: Premissas de 2027 no grupo `reforma_2027`, bloqueando só o exercício de 2027

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | DEFINE (AT-407) + evidência (`request_calculation` bloqueia qualquer premissa pendente) |

**Context:** As alíquotas não têm sugestão e ficam pendentes; se bloqueassem tudo, o cálculo de 2026 dos ciclos 2 e 3 pararia em todos os dossiês.

**Choice:** Premissas `reforma.cbs_aliquota` e `reforma.ibs_aliquota` (tipo `ratio`, sem sugestão), `reforma.crescimento` (tipo `ratio`, sugestão 0), `reforma.creditos_base` por competência (tipo `decimal`, sugestão pelo livro ou pela conta 13101) e `conformidade.custo_anual` para `regime:SIMPLES_HIBRIDO`, todas no grupo `reforma_2027`. `request_calculation` e a projeção de 2026 ignoram pendências desse grupo; a projeção de 2027 as trata como bloqueio (prévia).

**Rationale:** Cumpre AT-407 sem regredir os ciclos 2 e 3.

**Alternatives Rejected:**
1. Gerar as premissas de 2027 só quando o usuário pedir 2027 — exigiria um segundo momento de sugestão e deixaria a tela inconsistente.
2. Sugerir alíquota padrão — contraria a decisão do Brainstorm (Q2).

**Consequences:**
- A lista de pendências da tela separa "2026" e "2027".

### Decision 4: Projeção 2027 por deslocamento da Projeção 2026

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | DEFINE (AT-406) |

**Context:** Não há documentos de 2027; a base é a Projeção 2026 com crescimento.

**Choice:** `shift_year(case_2026, growth)` gera 12 meses sintéticos de 2027 com `MonthFacts` de 2026 × (1 + crescimento) (receita, atividades, lucro, compras, ICMS; margem e folha/receita mantidas), séries de receita anterior (2026 projetado) para RBT12/RBA/RBAA de 2027 e premissas por mês escaladas (`reforma.creditos_base` = razão média dos meses realizados × receita do mês de 2027). Origem de cada mês de 2027: `projetado` com `base` = origem do mês correspondente de 2026.

**Rationale:** Reuso integral do Projetor do ciclo 3; RBT12 e limites de 2027 coerentes com 2026.

**Alternatives Rejected:**
1. Projetar 2027 diretamente dos meses realizados — ignora estimados/orçamento de 2026.

**Consequences:**
- A projeção de 2027 depende da de 2026 (mesma chamada, sem gravar a de 2026).

### Decision 5: Livro de Apuração como documento opcional com R7 condicional

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | DEFINE (AT-410 a AT-416, Clarification 2) |

**Context:** O livro não pode alterar "competência completa" (quatro documentos) nem os snapshots/goldens existentes; só entra antes da homologação.

**Choice:** `DocType.LIVRO_ICMS_ALTERDATA` (classificação pelo título "REGISTRO DE APURAÇÃO DO ICMS" e período "Mês ou Período/Ano"); `DOC_TYPES` da `SnapshotView` permanece com quatro tipos. R7 é gerada só para competências com livro; usa o alvo de mapeamento novo `compras_mercadorias` (padrão do balancete: conta 13101) e a tolerância do escritório; divergência sem justificativa bloqueia a homologação como R1–R6. Saídas × receita do PGDAS-D: validação informativa (`status = warn`), sem bloqueio.

**Rationale:** Mesmo pipeline e mesmas garantias dos documentos do ciclo 1.

**Alternatives Rejected:**
1. R7 sempre (com `missing_source` sem livro) — geraria pendência em todos os dossiês existentes.

**Consequences:**
- Constraints de `source_files.doc_type`, `reconciliations.rule` e `account_mappings.target` ampliadas.

### Decision 6: Política de decisão de 2027 em arquivo próprio

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | Evidência (golden `decisao_2026` fixa `decision_version` 2026.1.0) |

**Context:** A sensibilidade de 2027 tem uma sexta variável (alíquota da CBS) e ressalvas próprias.

**Choice:** `services/worker/rules/decisao_2027.json` (versão 2027.1.0): as 5 variáveis do ciclo 3 + `cbs` (multiplicador 0,50–1,50 da alíquota informada), ressalvas de 2027 (regras não conferidas, alíquotas informadas pelo escritório, repartição do DAS por hipótese, mix de vendas não considerado). `load_decision_params` recebe o exercício; 2026 continua em `rules/decisao.json`.

**Rationale:** Não altera versão/hash da política de 2026.

**Alternatives Rejected:**
1. Editar `decisao.json` — mudaria o hash e a versão do golden aprovado.

**Consequences:**
- `config.py` ganha `decision_params_dir` (mesma pasta de regras).

---

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `services/worker/rules/2027/manifest.json` | Create | Versão 2027.1.0 e arquivos do exercício | (general) | None |
| 2 | `services/worker/rules/2027/consumo.json` | Create | CBS/IBS, base, créditos, CFOPs creditáveis | (general) | 1 |
| 3 | `services/worker/rules/2027/simples.json` | Create | Anexos 2027 com repartição `cbs`/`ibs`, `hibrido: true` | (general) | 1 |
| 4 | `services/worker/rules/2027/presumido.json` | Create | Presumido sem PIS/Cofins | (general) | 1 |
| 5 | `services/worker/rules/2027/real.json` | Create | Real sem PIS/Cofins | (general) | 1 |
| 6 | `services/worker/rules/2027/encargos.json` | Create | Cópia de 2026 | (general) | 1 |
| 7 | `services/worker/rules/2027/elegibilidade.json` | Create | Cópia de 2026 | (general) | 1 |
| 8 | `services/worker/rules/2027/atividades.json` | Create | Cópia de 2026 | (general) | 1 |
| 9 | `services/worker/rules/decisao_2027.json` | Create | Política de decisão 2027 (6 variáveis, ressalvas) | (general) | None |
| 10 | `services/worker/src/worker/engine/rules.py` | Modify | `RuleSet.consumo`; validação de `consumo.json` quando presente | (general) | 2 |
| 11 | `services/worker/src/worker/engine/decision_params.py` | Modify | Carregar a política por exercício | (general) | 9 |
| 12 | `services/worker/src/worker/config.py` | Modify | Política por exercício (`decisao.json` / `decisao_<ano>.json`) | (general) | 11 |
| 13 | `services/worker/src/worker/engine/memory.py` | Modify | `SIMPLES_HIBRIDO` e `regimes_for(rules)` | (general) | 10 |
| 14 | `services/worker/src/worker/engine/cbs_ibs.py` | Create | Débito, crédito e saldo de CBS/IBS por mês | (general) | 10 |
| 15 | `services/worker/src/worker/engine/presumido.py` | Modify | CBS/IBS no lugar de PIS/Cofins quando `rules.consumo` | (general) | 14 |
| 16 | `services/worker/src/worker/engine/real.py` | Modify | CBS/IBS no lugar de PIS/Cofins quando `rules.consumo` | (general) | 14 |
| 17 | `services/worker/src/worker/engine/simples.py` | Modify | Repartição 2027 e modo híbrido | (general) | 14 |
| 18 | `services/worker/src/worker/engine/calculate.py` | Modify | Iterar `regimes_for(rules)`; motor `SIMPLES_HIBRIDO` | (general) | 13, 15, 16, 17 |
| 19 | `services/worker/src/worker/engine/eligibility.py` | Modify | Elegibilidade do `SIMPLES_HIBRIDO` = Simples | (general) | 13 |
| 20 | `services/worker/src/worker/engine/assumptions.py` | Modify | Premissas do grupo `reforma_2027`; conformidade do híbrido | (general) | 24 |
| 21 | `services/worker/src/worker/engine/projection.py` | Modify | `shift_year` para 2027 | (general) | 20 |
| 22 | `services/worker/src/worker/engine/sensitivity.py` | Modify | Variável `cbs` (alavanca na alíquota) | (general) | 21 |
| 23 | `services/worker/src/worker/engine/recommendation.py`, `services/worker/src/worker/engine/decision.py` | Modify | Quatro alternativas; `project(year)`; bloqueio por alíquota ausente | (general) | 18, 21, 22 |
| 24 | `services/worker/src/worker/models.py`, `services/worker/src/worker/classify.py`, `services/worker/src/worker/parsers/__init__.py` | Modify | `LIVRO_ICMS_ALTERDATA` e sua classificação | (general) | None |
| 25 | `services/worker/src/worker/parsers/livro_icms_alterdata.py` | Create | Parser das entradas/saídas por CFOP | (general) | 24 |
| 26 | `services/worker/src/worker/validations.py` | Modify | Somas do livro; saídas × PGDAS-D informativa | (general) | 25 |
| 27 | `services/worker/src/worker/reconcile.py` | Modify | R7 condicional | (general) | 25 |
| 28 | `services/worker/src/worker/report_pdf.py` | Modify | Quatro alternativas e título do exercício | (general) | 23 |
| 29 | `services/worker/src/worker/pipeline.py`, `services/worker/src/worker/db.py` | Modify | Regras e política por exercício no job `project`; pendências por grupo | (general) | 23 |
| 30 | `supabase/migrations/20260925000004_reforma_2027.sql` | Create | Tipo de documento, R7, alvo `compras_mercadorias`, `SIMPLES_HIBRIDO`, `request_projection(uuid, integer)`, pendências por grupo | (general) | None |
| 31 | `supabase/tests/reforma_2027.test.sql` | Create | pgTAP: pendências de 2027 não bloqueiam 2026, regime novo, R7, RPC por exercício | (general) | 30 |
| 32 | `services/worker/tests/test_livro_icms.py` | Create | Parser, validações, classificação e CNPJ do livro de 08/2026 | (general) | 25, 26 |
| 33 | `services/worker/tests/test_reconcile.py` | Modify | R7 (bate ao centavo na amostra; divergência) | (general) | 27 |
| 34 | `services/worker/tests/test_engine_cbs_ibs.py` | Create | CBS/IBS no Presumido, no Real, no Simples por dentro e no híbrido; 2026 inalterado | (general) | 18 |
| 35 | `services/worker/tests/test_decisao_2027.py` | Create | Deslocamento, crescimento, bloqueio sem alíquota, 6 variáveis, 4 alternativas | (general) | 23 |
| 36 | `services/worker/tests/test_reforma_pipeline.py` | Create | Integração: livro → homologação → premissas → projeção 2027 → PDF; ≤ 60 s | (general) | 29, 30 |
| 37 | `services/worker/tests/golden/decisao_2027.json`, `services/worker/tests/test_decisao_golden.py` | Create / Modify | Golden de 2027 aprovado no build (com as alíquotas informadas) | (general) | 35 |
| 38 | `services/worker/tests/conftest.py` | Modify | Amostra do livro, mapeamento `compras_mercadorias`, regras 2027 | (general) | 24 |
| 39 | `apps/web/src/lib/database.types.ts` | Modify | Regenerar tipos | (general) | 30 |
| 40 | `apps/web/src/lib/format.ts`, `apps/web/src/lib/schemas.ts`, `apps/web/src/lib/schemas.test.ts` | Modify | Rótulos (híbrido, livro, R7, grupo de 2027, CBS/IBS), alvo de mapeamento | (general) | 39 |
| 41 | `apps/web/src/components/ComparisonTable.tsx`, `apps/web/src/components/ProjectionTable.tsx`, `apps/web/src/components/RecommendationPanel.tsx` | Modify | Regimes dinâmicos (3 ou 4) | (general) | 40 |
| 42 | `apps/web/src/app/(app)/cases/[id]/planning/page.tsx`, `apps/web/src/app/(app)/cases/[id]/planning/projection/actions.ts`, `apps/web/src/app/(app)/cases/[id]/planning/projection/[projId]/page.tsx` | Modify | "Projetar 2027", premissas separadas por exercício, título do exercício | (general) | 41 |
| 43 | `apps/web/src/app/(app)/admin/page.tsx` | Modify | Rótulo do alvo `compras_mercadorias` | (general) | 40 |
| 44 | `scripts/verify.mjs`, `README.md` | Modify | Amostra do livro no gate; seção do ciclo 4 | (general) | 36 |
| 45 | `kb/reforma-tributaria/concepts/simples-na-reforma.md` | Modify | Registrar a hipótese da repartição de 2027 e a exclusão de ICMS/ISS da base (art. 12, § 2º) com fontes | (general) | None |

**Total Files:** 45

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1–45 | Nenhum catálogo de agentes no projeto; mesmo executor dos ciclos 1–3 |

**Agent Discovery:** Not available

---

## Code Patterns

### Pattern 1: CBS/IBS mensal com saldo credor

```python
def month_lines(regime: str, comp: str, receita: Decimal, devolucoes: Decimal, creditos: Decimal,
                a: Assumptions, rules: RuleSet, saldo: dict) -> list[Line]:
    """Débito = (receita − devoluções) × alíquota; crédito = base de créditos × alíquota + saldo anterior."""
    lines = []
    for tax, key in (("cbs", "reforma.cbs_aliquota"), ("ibs", "reforma.ibs_aliquota")):
        if a.raw(key) is None:
            raise MissingRule("alíquota de " + tax.upper() + " de " + comp[:4] + " não confirmada")
        rate = a.decimal(key)
        base = max(ZERO, receita - devolucoes)
        credito = creditos * rate + saldo.get(tax, ZERO)
        devido = max(ZERO, base * rate - credito)
        saldo[tax] = max(ZERO, credito - base * rate)
        lines.append(Line(regime, comp, tax, money(base), rate, money(devido), "...",
                          rules.ref("consumo", tax), origin=a.origin(key), verified=False))
    return lines
```

### Pattern 2: Regimes por exercício

```python
REGIMES = ("SIMPLES", "PRESUMIDO", "REAL")
HIBRIDO = "SIMPLES_HIBRIDO"

def regimes_for(rules: RuleSet) -> tuple:
    return REGIMES + ((HIBRIDO,) if rules.simples.get("hibrido") else ())
```

### Pattern 3: Pendências por exercício no banco

```sql
select count(*), array_agg(label order by grp, key, scope)
       filter (where status = 'pending' and grp <> 'reforma_2027')
  into v_total, v_pending
  from public.assumptions where case_id = p_case_id;
```

---

## Data Flow

```text
1. Upload do Livro de Apuração (antes da homologação)
   classify → LIVRO_ICMS_ALTERDATA → parser (CFOP × colunas, página) → validações de soma
   │  CNPJ divergente → cnpj_mismatch; layout desconhecido → unclassified
   ▼
2. Conciliação: R1–R6 + R7 (se há livro na competência) → divergência sem justificativa bloqueia a homologação
   ▼
3. Homologação (snapshot inclui o livro como documento; competência completa segue com 4 documentos)
   ▼
4. suggest(): grupo reforma_2027 — alíquotas pendentes (sem sugestão), crescimento 0%, base de créditos por mês
   (livro: compras + frete; sem livro: débitos da conta 13101), conformidade do híbrido
   ▼
5. request_projection(case, 2027) → job project(year=2027)
   worker: regras 2027 + decisao_2027; pendências do grupo reforma_2027 → bloqueio (prévia)
   Projeção 2026 (ciclo 3) → shift_year(2027, crescimento) → motor 2027 (4 alternativas)
   → sensibilidade (6 variáveis) → recomendação → projections + recommendations (rascunho)
   │  idempotência: (snapshot, premissas, rules_hash 2027, decision_hash 2027, limiar)
   ▼
6. Fluxo do ciclo 3: envio → aprovação do responsável técnico → emissão do PDF "exercício 2027"
```

---

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| Supabase Postgres | DB (psycopg no worker; RPC/select na web) | Service role no worker; JWT + RLS na web | bidirectional | Retry do job (3 tentativas); erros de negócio P0001/P0002/42501 na tela |
| Supabase Storage | SDK/HTTP | Service role no worker; JWT na web | bidirectional | Mesmo tratamento dos ciclos 1 e 3 |

---

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Parser, classificação, validações e CNPJ do livro (AT-410, AT-411, AT-416) | `services/worker/tests/test_livro_icms.py` | pytest | Totais de 08/2026 (entradas R$ 158.503,98; saídas R$ 205.577,54) |
| Unit | R7 (AT-412, AT-413) | `services/worker/tests/test_reconcile.py` | pytest | Diferença R$ 0,00 na amostra; divergência construída |
| Unit | CBS/IBS por regime e exercício (AT-401 a AT-405) | `services/worker/tests/test_engine_cbs_ibs.py` | pytest | Sem PIS/Cofins/IPI em 2027; 2026 igual aos goldens |
| Unit | Projeção 2027, bloqueio, sensibilidade e recomendação (AT-406 a AT-409) | `services/worker/tests/test_decisao_2027.py` | pytest | Asserções de estado e valores |
| Unit (golden) | Projeção 2027 da amostra (AT-419) | `services/worker/tests/test_decisao_golden.py`, `golden/decisao_2027.json` | pytest | Igualdade exata com golden aprovado |
| Integration | Livro → homologação → projeção 2027 → PDF; ≤ 60 s (AT-414, AT-415, AT-417, AT-418) | `services/worker/tests/test_reforma_pipeline.py` | pytest + Postgres local | Estados, tempo e PDF |
| Database | Pendências por exercício, regime novo, R7, RPC por exercício | `supabase/tests/reforma_2027.test.sql` | pgTAP | Todos os asserts ok |
| Regression | Goldens dos ciclos 2 e 3 (AT-420) | `services/worker/tests/test_engine_calculate.py`, `test_decisao_golden.py` | pytest | Igualdade exata |
| E2E / Verify Gate | Gate do DEFINE | `scripts/verify.mjs` | `npm run verify` | exit 0 |

---

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Alíquota de 2027 não confirmada | Pendência do grupo `reforma_2027` / `MissingRule` em `cbs_ibs` | Recomendação `bloqueado` com prévia; regimes afetados "não calculado" com motivo | No | Log `projection.blocked` |
| Livro com soma inconsistente | Validação de soma | Validação `fail` com diferença; homologação segue as regras do ciclo 1 | No | `validations` |
| R7 divergente | Conciliação | Exige justificativa para homologar | No | `reconciliations` |
| Livro de outro CNPJ / layout desconhecido | classify | `cnpj_mismatch` / `unclassified` | No | Status do arquivo |
| Documento em dossiê homologado | Trigger do ciclo 1 | Recusa; base de créditos pela premissa manual | No | Erro na tela |
| Regras 2027 ausentes/inválidas | `load_rules` | `RulesError` no primeiro job de 2027; 2026 continua | No | Log do job |
| Falha inesperada no worker | Exceção | Retry com backoff (3) | Yes | `job.retry`/`job.failed` |

---

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `RULES_DIR`, `RULES_EXERCISE` | path, string | existentes; exercício 2026 padrão, 2027 carregado sob demanda | No | Regras por exercício |
| `DECISION_PARAMS` | path | existente (2026); 2027 = `decisao_2027.json` na mesma pasta | No | Política de decisão por exercício |
| `reforma.cbs_aliquota`, `reforma.ibs_aliquota` | premissa (ratio) | escritório, por dossiê; sem padrão | No | Alíquotas de 2027 |
| `reforma.crescimento` | premissa (ratio) | sugestão 0 | No | Crescimento da receita em 2027 |

---

## Security Considerations

- O livro contém razão social, inscrição estadual e CNPJ da empresa (pessoa jurídica), sem CPF; segue fora do Git em `docs/Amostras/` e no Storage privado por escritório.
- Novas constraints e RPCs mantêm RLS por escritório; `request_projection(uuid, integer)` valida membro e dossiê homologado como a versão atual.
- Premissas de alíquota são confirmadas com justificativa e auditadas (`confirm_assumption`), como as demais.
- Logs com IDs e códigos; nenhum valor do livro em log.

---

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | `file.extracted` com `doc_type=LIVRO_ICMS_ALTERDATA`; `projection.done`/`projection.blocked` com `year` | Diagnóstico de importação e de bloqueio por alíquota |
| Metrics | `duration_ms` e `engine_runs` por projeção de 2027 | AT-417 (≤ 60 s) |
| Tracing | N/A | Um job por projeção |

---

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| AT-401, AT-420 | Decisions 1–2 (2026 intacto) | goldens dos ciclos 2 e 3 |
| AT-402 a AT-405 | Regras 2027, `cbs_ibs.py`, `SIMPLES_HIBRIDO` | `test_engine_cbs_ibs.py` |
| AT-406, AT-409 | `shift_year`, variável `cbs` | `test_decisao_2027.py` |
| AT-407 | Decision 3 | `test_decisao_2027.py`, pgTAP |
| AT-408, AT-418 | Recomendação e PDF com 4 alternativas | `test_decisao_2027.py`, `test_reforma_pipeline.py` |
| AT-410, AT-411, AT-416 | Parser e validações do livro | `test_livro_icms.py` |
| AT-412, AT-413 | R7 | `test_reconcile.py`, pgTAP |
| AT-414, AT-415 | Sugestão da base de créditos; trigger do ciclo 1 | `test_reforma_pipeline.py` |
| AT-417 | Projeção 2027 dimensionada | `test_reforma_pipeline.py` |
| AT-419 | Golden `decisao_2027` | `test_decisao_golden.py` |
| Verify Gate | `npm run verify` | exit 0 |

---

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Repartição do DAS de 2027 diferente da hipótese A-401 | Simples por dentro/híbrido de 2027 incorretos | `verificado: false`, ressalva no PDF, correção = nova versão 2027.x | Médio |
| Alterar `presumido.py`/`real.py`/`simples.py` regredir 2026 | Goldens quebram | Ramo por `rules.consumo`; goldens no Verify Gate | Baixo |
| Parser do livro com uma única amostra | Outros meses/layouts falham | Validações de soma e `unclassified`; nova amostra = ajuste | Médio |
| Premissas de 2027 pendentes confundirem o usuário em 2026 | Atrito | Grupo separado na tela e pendências por exercício | Baixo |
| Alíquotas informadas incorretamente | Recomendação errada | Justificativa, auditoria, sensibilidade da CBS e aprovação do RT | Médio |

---

## Advisor Ledger

None — no formal external design review.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-25 | SDD Design by RDD | Initial version |

---

## Next Step

Execute o **SDD Build by RDD**.
