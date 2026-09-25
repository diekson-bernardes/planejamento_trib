# DESIGN: Motor Tributário — Elegibilidade e Cálculo dos Regimes (ciclo 2)

> Technical design for implementing Motor Tributário — Elegibilidade e Cálculo dos Regimes (ciclo 2)

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | MOTOR_TRIBUTARIO |
| **Date** | 2026-09-24 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_MOTOR_TRIBUTARIO.md` |
| **DEFINE** | `sdd/DEFINE_MOTOR_TRIBUTARIO.md` |
| **UX REVIEW** | N/A |
| **LLM Prompts** | false |
| **Status** | Ready for Build |

Base técnica observada: código do ciclo 1 na branch `feat/importacao-conciliacao` (worker Python em `services/worker`, migrations em `supabase/migrations`, site Next.js 16 em `apps/web`, Verify Gate `scripts/verify.mjs`).

---

## Architecture Overview

```text
 Analista (site)                                   Regras versionadas (Git)
   │ 1. "Iniciar planejamento"                     services/worker/rules/2026/*.json
   ▼                                                        │ versão + hash
┌──────────────────────────────┐   RPC request_planning     │
│ apps/web  /cases/[id]/planning│──────────────┐            │
│  • premissas (confirmar/alterar)             │            │
│  • calcular · simulações · comparativo       ▼            ▼
└──────────▲───────────────────┘   ┌─────────────────────────────────────────┐
           │ leitura (RLS)          │ Postgres: jobs (suggest_assumptions,     │
           │                        │   calculate, export_simulation)          │
           │                        │ snapshots (ciclo 1, imutável)            │
           │                        │ assumptions · simulations ·              │
           │                        │ simulation_lines · audit_events          │
           │                        └───────────────▲─────────────────────────┘
           │                                        │ claim job / grava resultado
           │                        ┌───────────────┴─────────────────────────┐
           │                        │ services/worker — worker.engine          │
           │                        │  SnapshotView → competências completas   │
           │                        │  assumptions: sugestões + hash           │
           │                        │  eligibility → simples · presumido ·     │
           │                        │  real · payroll → Line[] (memória)       │
           │                        │  calculate: result_hash, idempotência    │
           │                        └───────────────┬─────────────────────────┘
           │                                        │ XLSX da memória
           └──────────── URL assinada ◄──── Storage documents/<office>/<case>/simulations/
```

---

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| Rule Set | Tabelas de anexos, repartição, presunções, alíquotas, limites, encargos, elegibilidade e perfis de atividade, com vigência e fonte legal | Arquivos JSON versionados em `services/worker/rules/2026/` + `manifest.json` | — | Regras carregadas, versão e hash SHA-256 | — |
| Rules Loader | Lê, valida e expõe as regras; recusa regra fora de vigência | pydantic + `json` | Arquivos de regras | `RuleSet` imutável | Rule Set |
| Snapshot View | Lê o conteúdo do snapshot homologado e expõe fatos por documento e competência; identifica competências completas | Python puro | `snapshots.content` | Fatos, competências completas/excluídas | Snapshot do ciclo 1 |
| Activity Mapper | Converte a descrição de atividade do PGDAS-D em perfil (anexo, classe de presunção, ST, monofásico, cumulatividade) | Padrões textuais do `atividades.json` | Descrições 2.7 do PGDAS-D | Perfil de atividade | Rules Loader |
| Assumptions | Gera premissas sugeridas com origem; calcula o hash das premissas confirmadas | Python puro + tabela `assumptions` | Snapshot View, perfis | Premissas sugeridas; hash | Rules Loader, Snapshot View, Activity Mapper |
| Eligibility | Avalia Simples, Presumido e Real: elegível, alerta, inelegível, indeterminado | Funções puras | Fatos, premissas, regras | `EligibilityResult` por regime | Rules Loader |
| Payroll | Encargos patronais por regime e competência | Funções puras | Bases da folha (snapshot), premissas RAT/FAP/terceiros | Linhas de memória | Rules Loader |
| Simples Engine | DAS mensal por atividade (RBT12, Fator R, faixa, efetiva, repartição, faixa 5 para ICMS/ISS, exclusões) | Funções puras, `Decimal` | Fatos PGDAS-D, perfis, premissas | Linhas de memória | Rules Loader, Activity Mapper, Payroll |
| Presumido Engine | IRPJ/CSLL trimestrais (presunção, LC 224, adicional) + PIS/Cofins cumulativo mensal + ICMS/ISS por premissa | Funções puras, `Decimal` | Receitas por classe, premissas | Linhas de memória | Rules Loader, Activity Mapper, Payroll |
| Real Engine | Lucro ajustado trimestral (reclassificação do lucro da DRE para o regime, adições, exclusões, trava de 30%) + PIS/Cofins não cumulativo com créditos e parcela cumulativa | Funções puras, `Decimal` | Fatos DRE/balancete, premissas | Linhas de memória, saldos de prejuízo | Rules Loader, Payroll |
| Calculator | Orquestra competências, elegibilidade e regimes; totaliza; calcula `result_hash`; aplica "não calculado" quando falta regra | Python puro | Snapshot View, premissas, RuleSet | `SimulationResult` | Todos os engines |
| Worker Jobs | `suggest_assumptions`, `calculate`, `export_simulation` na fila existente | Extensão de `pipeline.py`/`db.py` | Jobs | Premissas, simulações, XLSX | Calculator, Storage |
| DB Schema | Tabelas `assumptions`, `simulations`, `simulation_lines`; RPCs `request_planning`, `confirm_assumption`, `request_calculation`, `request_simulation_export`; RLS e append-only | SQL (migration) | RPCs do site, gravações do worker | Dados com RLS | Tenancy e snapshots do ciclo 1 |
| Planning UI | Premissas, disparo do cálculo, lista de simulações, comparativo, drill-down e exportação | Next.js App Router + server actions | Ações do usuário | Chamadas RPC, páginas | DB Schema |

---

## Key Decisions

### Decision 1: Motor Python no worker, lendo somente o snapshot homologado

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | Brainstorm (Approach A) + DEFINE (Constraints) |

**Context:** O cálculo precisa ser reproduzível e auditável; as tabelas vivas do ciclo 1 mudam até a homologação.

**Choice:** O motor recebe apenas `snapshots.content` + `snapshots.sha256` + premissas confirmadas + `RuleSet`. Um `SnapshotView` indexa os valores do snapshot por `(doc_type, competence, field_key, column, section)`.

**Rationale:** O snapshot é imutável e já contém valores efetivos, ajustes e conciliações; reusa a fila, o `Decimal` e o pytest do ciclo 1.

**Alternatives Rejected:**
1. Ler `effective_values` — dados poderiam divergir do que foi homologado.
2. Motor em SQL ou TypeScript — rejeitados no Brainstorm.

**Consequences:**
- O planejamento só existe para dossiês homologados (AT-102).
- O worker precisa carregar o JSON do snapshot (≈ 1 MB para 1 000 valores; desprezível).

### Decision 2: Regras em JSON versionado no repositório, com vigência 2026

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (Clarifications: vigência 2026; regras versionadas) + clarificação técnica |

**Context:** PRD exige regras parametrizadas, com fonte legal e versão registrada em cada resultado.

**Choice:** `services/worker/rules/2026/` com `manifest.json` (versão semântica, vigência, lista de arquivos) e um arquivo por domínio. `rules_hash` = SHA-256 da concatenação canônica dos arquivos listados. Cada regra carrega `fonte` e `verificado` (true só quando conferida na fonte primária). Competência fora de 2026 → regime "não calculado".

**Rationale:** JSON dispensa dependência nova (`json` da biblioteca padrão); versionar no Git dá histórico e revisão por pull request.

**Alternatives Rejected:**
1. YAML — exige `pyyaml`; ganho só de legibilidade.
2. Regras em tabela com tela de publicação — fora de escopo (YAGNI).

**Consequences:**
- Mudança de regra = nova versão no manifest + deploy do worker (Dockerfile copia `rules/`).
- Linhas de memória calculadas com regra `verificado: false` levam o alerta "regra não conferida na fonte primária".

### Decision 3: Premissas como registros por dossiê, com sugestão, confirmação e hash

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (Goals, AT-103 a AT-105) |

**Context:** ICMS/ISS, créditos, adições/exclusões, prejuízo, RAT/FAP, terceiros, perfis de atividade e declarações de elegibilidade não vêm dos documentos.

**Choice:** Tabela `assumptions` (uma linha por `key` + `scope` por dossiê) com `suggested_value`, `suggested_origin`, `value`, `status` (`pending` | `confirmed`), `justification`, `confirmed_by`, `confirmed_at`. Confirmação só pela RPC `confirm_assumption`, que exige justificativa (≥ 5) quando o valor difere do sugerido e grava auditoria. `assumptions_hash` = SHA-256 do JSON canônico de `(key, scope, value)` confirmados.

**Rationale:** Separa dado extraído, premissa e regra (PRD §1) e dá trilha completa.

**Alternatives Rejected:**
1. Premissas como JSON dentro da simulação — perde reutilização entre execuções e auditoria por campo.

**Consequences:**
- `request_calculation` falha se houver premissa `pending` (AT-105).
- Declarações de elegibilidade aceitam o valor `nao_informado`; confirmar "não informado" é válido e torna o regime indeterminado (AT-117), sem bloquear o cálculo.

### Decision 4: Reclassificação do lucro da DRE para o Lucro Real

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | Clarificação técnica (dados observados: DRE da amostra sob o Simples) |

**Context:** A DRE de um optante do Simples já desconta o DAS (conta Simples Nacional 23.430,47 em 08/2026) e não tem CPP, PIS/Cofins nem IRPJ/CSLL do regime normal. Usar o lucro da DRE sem ajuste subestima o custo do Real.

**Choice:** Lucro antes de IRPJ/CSLL no Real = lucro líquido da DRE + despesa de Simples da DRE (conta mapeada `simples_despesa`) − encargos patronais do regime (Payroll) − PIS/Cofins do regime − ICMS/ISS do regime não já registrados na DRE (premissa `icms_iss_ja_na_dre`, sugerida `true` quando há conta ICMS na DRE). Cada parcela vira linha de memória `real.reclassificacao`.

**Rationale:** O comparativo precisa refletir o lucro que existiria no regime simulado.

**Alternatives Rejected:**
1. Usar o lucro da DRE sem ajuste — viés a favor do Real.
2. Exigir DRE refeita pelo analista — trabalho manual que o motor pode fazer com memória.

**Consequences:**
- O golden de 08/2026 do Real depende dessa reclassificação e é aprovado pelo usuário (A-005 do DEFINE).

### Decision 5: Simulação imutável e idempotente por hashes

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (AT-106, AT-121, AT-122) |

**Context:** Mesmas entradas devem produzir o mesmo resultado sem duplicar; mudanças devem gerar nova simulação.

**Choice:** `simulations` com `UNIQUE (case_id, snapshot_sha256, assumptions_hash, rules_hash)`. O worker calcula os três hashes; se a simulação já existe com `status = done`, o job termina sem gravar outra. `result_hash` = SHA-256 do JSON canônico das linhas ordenadas. `simulations` e `simulation_lines` são append-only após `done` (trigger).

**Rationale:** Reprodutibilidade comprovável e histórico preservado.

**Alternatives Rejected:**
1. Sobrescrever a simulação a cada cálculo — perde histórico e comparação.

**Consequences:**
- A tela lista todas as simulações do dossiê, a mais recente primeiro.

### Decision 6: Competência completa e trimestres parciais

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | Brainstorm (pergunta 2) + DEFINE (AT-101, AT-115) |

**Context:** O snapshot da amostra tem PGDAS-D de 06–08/2026 e demais documentos só de 08/2026.

**Choice:** Competência completa = existe no snapshot arquivo `extracted` de cada um dos 4 `doc_type` com `competence` = mês. Simples, encargos, PIS/Cofins e ICMS/ISS são calculados só nesses meses; IRPJ/CSLL de Presumido e Real por trimestre civil com os meses completos disponíveis, `partial = true` se o trimestre tiver menos de 3. Adicional de IRPJ usa limite de R$ 20.000 × meses considerados.

**Rationale:** Não inventar dado ausente; comparabilidade entre regimes no mesmo conjunto de meses.

**Alternatives Rejected:**
1. Calcular o Simples em todos os meses com PGDAS-D — comparativo com bases diferentes entre regimes.

**Consequences:**
- A amostra atual produz uma competência (08/2026) e o trimestre 2026-T3 parcial.

### Decision 7: Regras do Simples observadas nas amostras

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (AT-107 a AT-110; A-001, A-004) + recálculo do DAS de 06/2026 |

**Context:** O DAS declarado é o caso dourado; regras mal parametrizadas quebram a igualdade ao centavo.

**Choice:** RBT12 = soma da série `receita_anterior.*` (interno + externo) dos 12 meses anteriores; divergência em relação ao `receita.rbt12` declarado gera alerta (usa o recalculado). Faixa pela tabela do anexo. Alíquota efetiva sem arredondamento; cada tributo = receita × efetiva × percentual de repartição, arredondado a centavos (ROUND_HALF_UP) por atividade. Faixa 6 com sublimite sem efeito (RBAA ≤ 3,6 mi e RBA ≤ 4,32 mi): ICMS/ISS = receita × efetiva da faixa 5 × repartição de ICMS/ISS da faixa 5. ST de ICMS e monofásico zeram a parcela correspondente. Fator R = folha 12 meses ÷ RBT12 (folha da série `folha_anterior.*` ou premissa `folha_12m`).

**Rationale:** Reproduz o DAS da amostra (verificado em 06/2026 no ciclo 1).

**Alternatives Rejected:**
1. Usar o RBT12 declarado sem recalcular — esconde erro de série.

**Consequences:**
- A repartição de todos os anexos/faixas precisa ser transcrita da LC 123/2006 no Build; só Anexo I faixas 5 e 6 estão conferidas (`verificado: true`).

### Decision 8: Reuso da fila e do Storage do ciclo 1

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | Clarificação técnica (código do ciclo 1) |

**Context:** O ciclo 1 já tem fila idempotente, backoff, Storage privado por escritório e auditoria.

**Choice:** Novos `kind` de job (`suggest_assumptions`, `calculate`, `export_simulation`) na mesma tabela `jobs`; XLSX em `documents/<office>/<case>/simulations/<simulation_id>.xlsx`; eventos em `audit_events`.

**Rationale:** Nenhuma infraestrutura nova.

**Alternatives Rejected:**
1. Serviço separado para o motor — operação duplicada sem ganho.

**Consequences:**
- A migration amplia a constraint de `jobs.kind`.

---

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `supabase/migrations/20260925000001_motor.sql` | Create | `assumptions`, `simulations`, `simulation_lines`; ampliação de `jobs.kind`; RPCs `request_planning`, `confirm_assumption`, `request_calculation`, `request_simulation_export`; RLS; append-only; auditoria; recriar a política `documents_insert` bloqueando também `/simulations/` para usuários | (general) | None |
| 2 | `supabase/tests/motor.test.sql` | Create | pgTAP: RLS das novas tabelas, justificativa obrigatória, bloqueio por premissa pendente, dossiê não homologado, imutabilidade da simulação | (general) | 1 |
| 3 | `services/worker/rules/2026/manifest.json` | Create | Versão (`2026.1.0`), vigência, arquivos, fontes | (general) | None |
| 4 | `services/worker/rules/2026/simples.json` | Create | Anexos I–V: faixas, nominal, parcela a deduzir, repartição por faixa; teto, sublimite, tolerância 20%; Fator R 28% | (general) | 3 |
| 5 | `services/worker/rules/2026/presumido.json` | Create | Presunções IRPJ/CSLL por classe; LC 224 (limite, fator 1,10, vigências); IRPJ 15%, adicional 10% sobre 20 mil/mês, CSLL 9%; PIS 0,65%, Cofins 3% | (general) | 3 |
| 6 | `services/worker/rules/2026/real.json` | Create | IRPJ, adicional, CSLL, trava 30%, PIS 1,65%/Cofins 7,6%, parcela cumulativa 0,65%/3% | (general) | 3 |
| 7 | `services/worker/rules/2026/encargos.json` | Create | CPP 20%, faixas de RAT, FAP, terceiros por FPAS (515 = 5,8%), anexos com CPP no DAS | (general) | 3 |
| 8 | `services/worker/rules/2026/elegibilidade.json` | Create | Limites do Simples e do Presumido; declarações exigidas por regime e seus efeitos | (general) | 3 |
| 9 | `services/worker/rules/2026/atividades.json` | Create | Padrões de descrição do PGDAS-D → perfil (anexo, classe de presunção, ST, monofásico, cumulativo no Real) | (general) | 3 |
| 10 | `services/worker/src/worker/config.py` | Modify | `rules_dir` (env `RULES_DIR`, padrão `services/worker/rules`) | (general) | None |
| 11 | `services/worker/Dockerfile` | Modify | Copiar `rules/` para a imagem e definir `RULES_DIR` | (general) | 3 |
| 12 | `services/worker/src/worker/engine/__init__.py` | Create | Pacote do motor | (general) | None |
| 13 | `services/worker/src/worker/engine/memory.py` | Create | `Line`, `money()` (ROUND_HALF_UP), `canonical_hash()` | (general) | 12 |
| 14 | `services/worker/src/worker/engine/rules.py` | Create | `RuleSet`, `load_rules()`, validação, `rules_hash`, lookup por vigência | (general) | 3, 4, 5, 6, 7, 8, 9, 10, 13 |
| 15 | `services/worker/src/worker/engine/snapshot.py` | Create | `SnapshotView`: fatos por documento/competência, competências completas, séries do PGDAS-D | (general) | 13 |
| 16 | `services/worker/src/worker/engine/activities.py` | Create | `ActivityProfile` e mapeamento de descrições do PGDAS-D | (general) | 14, 15 |
| 17 | `services/worker/src/worker/engine/assumptions.py` | Create | Catálogo de premissas, geração de sugestões com origem, `assumptions_hash` | (general) | 14, 15, 16 |
| 18 | `services/worker/src/worker/engine/eligibility.py` | Create | Elegibilidade dos três regimes | (general) | 14, 15, 17 |
| 19 | `services/worker/src/worker/engine/payroll.py` | Create | Encargos patronais por regime | (general) | 14, 15, 17 |
| 20 | `services/worker/src/worker/engine/simples.py` | Create | DAS mensal por atividade | (general) | 14, 15, 16, 19 |
| 21 | `services/worker/src/worker/engine/presumido.py` | Create | Presumido trimestral + mensais | (general) | 14, 15, 16, 17, 19 |
| 22 | `services/worker/src/worker/engine/real.py` | Create | Real trimestral com reclassificação do lucro + PIS/Cofins | (general) | 14, 15, 16, 17, 19 |
| 23 | `services/worker/src/worker/engine/calculate.py` | Create | Orquestração, totais, ordenação, "não calculado", `result_hash` | (general) | 18, 20, 21, 22 |
| 24 | `services/worker/src/worker/db.py` | Modify | Ler snapshot, upsert de premissas sugeridas, leitura de confirmadas, gravação de simulação e linhas | (general) | 1 |
| 25 | `services/worker/src/worker/export_xlsx.py` | Modify | `build_simulation_xlsx()` (Resumo, Elegibilidade, Comparativo, Memória, Premissas) | (general) | 13 |
| 26 | `services/worker/src/worker/pipeline.py` | Modify | Jobs `suggest_assumptions`, `calculate`, `export_simulation` | (general) | 17, 23, 24, 25 |
| 27 | `services/worker/tests/conftest.py` | Modify | Fixture `snapshot_from_samples` (mesmo formato do `homologate_case`) e `rules` | (general) | 15 |
| 28 | `services/worker/tests/test_engine_rules.py` | Create | Carga, validação, hash estável, vigência 2026 | (general) | 14 |
| 29 | `services/worker/tests/test_engine_simples.py` | Create | DAS 06/07/08-2026 = PGDAS-D; faixa 5 para ICMS; ST zera ICMS; Fator R III × V | (general) | 20, 27 |
| 30 | `services/worker/tests/test_engine_presumido.py` | Create | Golden KB 54.570,00; LC 224 com vigências IRPJ/CSLL; trimestre parcial | (general) | 21 |
| 31 | `services/worker/tests/test_engine_real.py` | Create | Golden KB 43.980,00; saldo de prejuízo; lucro negativo; parcela cumulativa (hospitalar); reclassificação | (general) | 22 |
| 32 | `services/worker/tests/test_engine_eligibility.py` | Create | Elegível, alerta, inelegível e indeterminado por regime | (general) | 18 |
| 33 | `services/worker/tests/test_engine_payroll_assumptions.py` | Create | Encargos por regime/anexo; sugestões com origem; hash de premissas | (general) | 17, 19, 27 |
| 34 | `services/worker/tests/test_engine_calculate.py` | Create | Competências completas, regra ausente, ordenação, idempotência do `result_hash`, golden 08/2026 aprovado | (general) | 23, 27, 35 |
| 35 | `services/worker/tests/golden/motor_202608.json` | Create | Golden de Presumido e Real de 08/2026 com `approved_by`/`approved_at` (gravado só após aprovação do usuário) | (general) | 23, 27 |
| 36 | `services/worker/tests/test_motor_pipeline.py` | Create | Integração com Postgres: sugerir → confirmar → calcular → simulação; bloqueio por pendência; idempotência; ≤ 60 s | (general) | 1, 26 |
| 37 | `apps/web/src/lib/database.types.ts` | Modify | Regenerar tipos (`npm run db:types`) | (general) | 1 |
| 38 | `apps/web/src/lib/schemas.ts` | Modify | `confirmAssumptionSchema` | (general) | None |
| 39 | `apps/web/src/lib/schemas.test.ts` | Modify | Testes do novo schema | (general) | 38 |
| 40 | `apps/web/src/lib/format.ts` | Modify | Rótulos de regimes, tributos, status de elegibilidade e de simulação | (general) | None |
| 41 | `apps/web/src/app/(app)/cases/[id]/planning/actions.ts` | Create | Server actions: iniciar planejamento, confirmar premissa, calcular, exportar | (general) | 37, 38 |
| 42 | `apps/web/src/components/AssumptionForm.tsx` | Create | Linha de premissa: sugerido, origem, confirmar/alterar com justificativa | (general) | 40, 41 |
| 43 | `apps/web/src/app/(app)/cases/[id]/planning/page.tsx` | Create | Competências, premissas agrupadas, botão calcular, lista de simulações | (general) | 41, 42 |
| 44 | `apps/web/src/components/ComparisonTable.tsx` | Create | Comparativo por tributo/regime e mensal, ordenado, com elegibilidade | (general) | 40 |
| 45 | `apps/web/src/components/SimulationLines.tsx` | Create | Drill-down da memória: base, alíquota, fórmula, regra/versão, origem | (general) | 40 |
| 46 | `apps/web/src/app/(app)/cases/[id]/planning/[simId]/page.tsx` | Create | Página da simulação | (general) | 44, 45 |
| 47 | `apps/web/src/app/api/simulations/[id]/export/route.ts` | Create | URL assinada do XLSX da simulação (RLS) | (general) | 37 |
| 48 | `apps/web/src/app/(app)/cases/[id]/page.tsx` | Modify | Link "Planejamento" quando homologado | (general) | 43 |
| 49 | `README.md` | Modify | Seção do motor: regras, premissas, jobs e testes | (general) | 26 |

**Total Files:** 49

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1–49 | Nenhum catálogo de agentes especializados no projeto |

**Agent Discovery:** Not available

---

## Code Patterns

### Pattern 1: Linha de memória e arredondamento

```python
# services/worker/src/worker/engine/memory.py
import hashlib
import json
from dataclasses import asdict, dataclass, field
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Line:
    regime: str          # SIMPLES | PRESUMIDO | REAL
    period: str          # "2026-08" (mensal) ou "2026-T3" (trimestral)
    tax: str             # irpj, adicional_irpj, csll, pis, cofins, cpp, rat, terceiros, icms, iss, ipi
    base: Decimal
    rate: Decimal        # alíquota efetiva/nominal aplicada, sem arredondar
    amount: Decimal      # money(base * rate) ou valor derivado
    formula: str         # texto legível: "receita 116.824,55 × efetiva 9,1591% × IRPJ 13,5%"
    rule_ref: str        # "simples.anexo_I.faixa_6.reparticao.irpj@2026.1.0"
    origin: dict = field(default_factory=dict)   # snapshot field_key/file_id/page ou assumption key
    activity: str | None = None
    partial: bool = False


def canonical_hash(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def lines_hash(lines: list[Line]) -> str:
    return canonical_hash([asdict(line) for line in lines])
```

### Pattern 2: Arquivo de regras com vigência e fonte

```json
{
  "domain": "simples",
  "version": "2026.1.0",
  "vigencia": ["2026-01-01", "2026-12-31"],
  "anexos": [
    {
      "anexo": "I",
      "faixas": [
        {
          "faixa": 6,
          "ate": "4800000.00",
          "nominal": "0.19",
          "deduzir": "378000.00",
          "reparticao": [
            ["irpj", "0.135"], ["csll", "0.10"], ["cofins", "0.2827"],
            ["pis", "0.0613"], ["cpp", "0.421"], ["icms", "0"]
          ],
          "fonte": "LC 123/2006, Anexo I",
          "verificado": true
        }
      ]
    }
  ]
}
```

Valores sempre como string decimal (nunca float); o loader converte para `Decimal`.

### Pattern 3: Cálculo do Simples por atividade (faixa 5 para ICMS/ISS)

```python
# services/worker/src/worker/engine/simples.py (trecho)
def effective_rate(rbt12: Decimal, band) -> Decimal:
    return (rbt12 * band.nominal - band.deduzir) / rbt12


def activity_lines(period, activity, receita, rbt12, anexo, sublimite_sem_efeito, rules) -> list[Line]:
    band = rules.simples.band(anexo, rbt12)
    efetiva = effective_rate(rbt12, band)
    local_band = band
    if band.faixa == 6 and sublimite_sem_efeito:
        local_band = rules.simples.band_by_number(anexo, 5)   # ICMS/ISS pela faixa 5
    local_rate = effective_rate(rbt12, local_band)
    lines = []
    for tax, share in band.reparticao:
        if tax in activity.zeroed_taxes:                    # ICMS-ST, monofásico, exportação
            continue
        rate = efetiva * share
        if tax in ("icms", "iss") and local_band is not band:
            rate = local_rate * local_band.share(tax)
        lines.append(Line("SIMPLES", period, tax, receita, rate, money(receita * rate),
                          formula="receita " + str(receita) + " × " + format(rate, ".6%"),
                          rule_ref=".".join(["simples", "anexo_" + anexo, "faixa_" + str(band.faixa), tax]) + "@" + rules.version,
                          origin=activity.origin, activity=activity.key))
    return lines
```

Na faixa 6 a repartição tem ICMS 0; o motor acrescenta a linha de ICMS/ISS pela faixa 5 quando o sublimite ainda não produz efeito e a atividade não tem ST.

### Pattern 4: RPC de confirmação de premissa

```sql
-- supabase/migrations/20260925000001_motor.sql (trecho)
create or replace function public.confirm_assumption(p_id uuid, p_value jsonb, p_justification text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.assumptions%rowtype;
begin
  select * into v from public.assumptions where id = p_id for update;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Premissa não encontrada' using errcode = 'P0002';
  end if;
  if p_value is distinct from v.suggested_value
     and (p_justification is null or length(trim(p_justification)) < 5) then
    raise exception 'Justificativa obrigatória ao alterar o valor sugerido' using errcode = 'P0001';
  end if;
  update public.assumptions
     set value = p_value, status = 'confirmed', justification = nullif(trim(p_justification), ''),
         confirmed_by = auth.uid(), confirmed_at = now()
   where id = p_id;
  perform public.write_audit(v.office_id, 'assumption.confirmed', 'assumptions', p_id,
    jsonb_build_object('suggested', v.suggested_value, 'previous', v.value),
    jsonb_build_object('value', p_value, 'justification', p_justification));
end;
$$;
```

### Pattern 5: Hash e idempotência da simulação no worker

```python
# services/worker/src/worker/pipeline.py (trecho do job calculate)
view = SnapshotView(snapshot["content"])
confirmed = db.load_confirmed_assumptions(self.conn, case_id, office_id)
key = (snapshot["sha256"].strip(), assumptions_hash(confirmed), self.rules.hash)
existing = db.find_simulation(self.conn, case_id, office_id, *key)
if existing is not None and existing["status"] == "done":
    return "simulação já existente"
result = calculate(view, confirmed, self.rules)
db.save_simulation(self.conn, case_id, office_id, key, result)
```

---

## Data Flow

```text
1. Iniciar planejamento (site → RPC request_planning)
   Valida dossiê homologado (senão erro "Planejamento exige dossiê homologado")
   → enfileira jobs(kind='suggest_assumptions', key='suggest:<case>:<snapshot_sha>')
   │
   ▼
2. Sugestões (worker)
   SnapshotView(snapshot.content) → competências completas/excluídas
   → perfis de atividade (atividades.json) → catálogo de premissas com valor sugerido + origem
   → upsert em assumptions (mantém valor já confirmado se a sugestão não mudou)
   │
   ▼
3. Revisão (site)
   Lista premissas por grupo (atividades, ICMS/ISS, PIS/Cofins, Real, folha, elegibilidade)
   → confirm_assumption(id, valor, justificativa) → audit_event 'assumption.confirmed'
   │
   ▼
4. Calcular (site → RPC request_calculation)
   Pendentes > 0 → erro com a lista (AT-105)
   → enfileira jobs(kind='calculate', key='calculate:<case>:<assumptions_hash SQL>')
   │
   ▼
5. Cálculo (worker, < 60 s)
   RuleSet(versão, hash) + SnapshotView + premissas confirmadas
   → para cada regime: elegibilidade; competências completas; regra vigente?
     não → status 'nao_calculado' + pendência técnica (AT-118)
   → Simples (mensal, por atividade) · Presumido (trimestral + mensal) · Real (trimestral + mensal)
   → Payroll por regime · ICMS/ISS por premissa
   → totais por regime e tributo; ordenação por total entre elegíveis
   → result_hash; se (snapshot, premissas, regras) já tem simulação done → termina sem gravar
   → grava simulations + simulation_lines numa transação
   │
   ▼
6. Comparativo (site)
   /cases/<id>/planning/<simId>: elegibilidade, quadro por tributo, mensal, trimestres parciais,
   drill-down linha → fórmula, regra@versão, origem (field_key/arquivo/página ou premissa)
   │
   ▼
7. Exportar (site → RPC request_simulation_export → job export_simulation)
   XLSX em documents/<office>/<case>/simulations/<simId>.xlsx → URL assinada 60 s
```

---

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| Supabase Postgres (worker) | `psycopg` (conexão existente) | `DATABASE_URL` (role de serviço) | bidirectional | Mesmo tratamento do ciclo 1: `TransientError` → backoff exponencial até `WORKER_MAX_ATTEMPTS`; depois `failed` |
| Supabase Postgres (site) | PostgREST/RPC com JWT | Sessão do usuário (RLS) | bidirectional | Erro exibido ao usuário; RPCs idempotentes por chave de job |
| Supabase Storage (worker) | REST (`SupabaseStorage`) | `SUPABASE_SERVICE_ROLE_KEY` | out | Timeout 30 s; 5xx → retry; job de exportação reenfileirável como no ciclo 1 |
| Arquivos de regras | Leitura local no start do worker | N/A | in | Arquivo inválido ou hash divergente do manifest → worker não inicia (falha explícita no log) |

---

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Carga/validação das regras, hash estável, vigência | `services/worker/tests/test_engine_rules.py` | pytest | Todos passam |
| Unit (golden) | DAS 06/07/08-2026 = PGDAS-D ao centavo; faixa 5 ICMS; ST; Fator R (AT-107 a AT-110) | `services/worker/tests/test_engine_simples.py` | pytest (`samples`) | Diferença ≤ R$ 0,01 por tributo |
| Unit (golden) | Presumido KB 54.570,00; LC 224; parcial (AT-111, AT-112, AT-115) | `services/worker/tests/test_engine_presumido.py` | pytest | Igualdade exata |
| Unit (golden) | Real KB 43.980,00 e saldo 87.000,00; hospitalar cumulativo; lucro negativo; reclassificação (AT-113, AT-114) | `services/worker/tests/test_engine_real.py` | pytest | Igualdade exata |
| Unit | Elegibilidade (AT-116, AT-117) | `services/worker/tests/test_engine_eligibility.py` | pytest | Status e motivos esperados |
| Unit | Encargos por regime; sugestões com origem; hash de premissas (AT-103, AT-119) | `services/worker/tests/test_engine_payroll_assumptions.py` | pytest | Todos passam |
| Unit (golden) | Competências completas, regra ausente, ordenação, `result_hash`, golden 08/2026 aprovado (AT-101, AT-118, AT-120, AT-121, AT-123, AT-126) | `services/worker/tests/test_engine_calculate.py`, `services/worker/tests/golden/motor_202608.json` | pytest (`samples`) | Igualdade com golden aprovado |
| Integration | Sugerir → confirmar → calcular → simulação; pendência bloqueia; nova simulação ao mudar premissa; ≤ 60 s (AT-105, AT-106, AT-122, AT-125) | `services/worker/tests/test_motor_pipeline.py` | pytest (`db`, `samples`) + Supabase local | Tempo ≤ 60 s e asserts passam |
| Integration (DB) | RLS, justificativa, dossiê não homologado, pendência, imutabilidade (AT-102, AT-104, AT-105, AT-124) | `supabase/tests/motor.test.sql` | pgTAP via `npx supabase test db` | Todos os asserts passam |
| Unit (web) | `confirmAssumptionSchema` | `apps/web/src/lib/schemas.test.ts` | vitest | Todos passam |
| Typecheck | Web | `apps/web/tsconfig.json` | `tsc --noEmit` | exit 0 |
| E2E / Verify Gate | Todos os anteriores | `scripts/verify.mjs` (sem alteração: já executa todo o pytest, pgTAP e web) | `npm run verify` | exit 0 |

---

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Dossiê não homologado | `request_planning` / `request_calculation` | Erro P0001 "Planejamento exige dossiê homologado" | No | Resposta da RPC |
| Premissa pendente | `request_calculation` conta `status = 'pending'` | Erro P0001 com as chaves pendentes | No | Resposta da RPC |
| Alteração sem justificativa | `confirm_assumption` | Erro P0001 | No | Auditoria só em sucesso |
| Nenhuma competência completa | `SnapshotView.complete_competences()` vazio | Simulação `failed` com `error_code = NO_COMPLETE_COMPETENCE` | No | Log `simulation.failed` |
| Regra ausente (ano ≠ 2026, anexo/faixa/atividade sem regra) | `RuleSet` retorna `None` | Regime `nao_calculado` + pendência técnica na simulação; demais regimes seguem | No | Contagem por regime no log |
| Atividade do PGDAS-D sem perfil | `ActivityMapper` sem padrão | Premissa `atividade.<n>.perfil` sem sugestão (pendente) | No | Log `assumption.unmapped_activity` |
| RBT12 recalculado ≠ declarado | Comparação em `simples.py` | Usa o recalculado e grava alerta na simulação | No | Alerta na memória |
| Arquivo de regras inválido | `load_rules()` na inicialização | Worker não inicia; erro explícito | No | Log `rules.invalid` |
| Falha de banco/Storage | Exceções `psycopg`/`httpx` | `TransientError`, backoff, idempotência por hashes | Yes | Log `job.retry` |
| Cálculo repetido | `UNIQUE (case_id, snapshot_sha256, assumptions_hash, rules_hash)` | Termina sem gravar outra simulação | N/A | Log `simulation.reused` |
| Escrita em simulação concluída | Trigger append-only | Exceção "simulação imutável" | No | Erro do Postgres |

---

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `RULES_DIR` | path | env / `services/worker/rules` (na imagem: `/app/rules`) | No | Diretório das regras versionadas |
| `RULES_EXERCISE` | string | env / `2026` | No | Subpasta de regras carregada |
| `rules/2026/manifest.json` → `version` | string | arquivo / `2026.1.0` | No | Versão gravada em cada simulação |
| `WORKER_POLL_SECONDS`, `WORKER_MAX_ATTEMPTS`, `WORKER_LEASE_SECONDS`, `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | vários | env (ciclo 1) | `DATABASE_URL` e chave de serviço: Yes | Reusados sem mudança |

---

## Security Considerations

- **Isolamento:** `assumptions`, `simulations` e `simulation_lines` têm `office_id` + RLS `is_member`; FKs compostas `(case_id, office_id)`; `motor.test.sql` entra no gate.
- **Escrita controlada:** usuários não têm INSERT/UPDATE direto nas novas tabelas; tudo passa por RPCs `security definer` que checam `is_member` e o estado do dossiê. O worker grava com a role de serviço, sempre filtrando `office_id`.
- **Imutabilidade:** simulações concluídas e suas linhas são append-only (trigger); premissas confirmadas só mudam por nova confirmação auditada.
- **PII:** o motor usa só valores numéricos e códigos; rótulos com nome de pessoa (ex.: conta de adiantamento a sócio) não são copiados para `simulation_lines.origin` — a origem guarda `field_key`, `account_code`, `file_id` e página.
- **Integridade das regras:** `rules_hash` gravado em cada simulação; o worker recusa iniciar com arquivo inválido.
- **Storage:** XLSX em `<office>/<case>/simulations/`; política de select por prefixo do ciclo 1 cobre o caminho; usuários não gravam nesse caminho (insert bloqueado para `exports/` e `simulations/`).

---

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | JSON por linha no worker: `suggest.generated`, `simulation.started`, `simulation.done` (duração, linhas, regimes calculados/não calculados), `simulation.reused`, `simulation.failed` (código) — só IDs e contagens | Diagnóstico de regra ausente e tempo |
| Metrics | Derivadas em SQL: duração `created_at → finished_at` por simulação; proporção de regimes `nao_calculado`; premissas alteradas × sugeridas | Meta de 60 s (AT-125) e qualidade das sugestões |
| Tracing | N/A — correlação por `case_id`, `simulation_id` e `job_id` | Fluxo assíncrono simples |

---

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| AT-101 competências completas | Decision 6, #15 | `test_engine_calculate.py` |
| AT-102 dossiê homologado | #1 (RPCs) | `motor.test.sql` |
| AT-103 sugestões com origem | Decision 3, #17 | `test_engine_payroll_assumptions.py` |
| AT-104 justificativa | Pattern 4, #1 | `motor.test.sql`, `schemas.test.ts` |
| AT-105 bloqueio por pendência | #1 (`request_calculation`) | `motor.test.sql`, `test_motor_pipeline.py` |
| AT-106 hashes gravados | Decision 5, #24 | `test_motor_pipeline.py` |
| AT-107 DAS = PGDAS-D | Decision 7, #20 | `test_engine_simples.py` |
| AT-108 faixa 5 para ICMS/ISS | Pattern 3, #20 | `test_engine_simples.py` |
| AT-109 ST/monofásico | #16, #20 | `test_engine_simples.py` |
| AT-110 Fator R | #20 | `test_engine_simples.py` |
| AT-111 Presumido KB | #21 | `test_engine_presumido.py` |
| AT-112 LC 224 | #5, #21 | `test_engine_presumido.py` |
| AT-113 Real KB | #22 | `test_engine_real.py` |
| AT-114 parcela cumulativa no Real | #9, #22 | `test_engine_real.py` |
| AT-115 trimestre parcial | Decision 6, #21, #22 | `test_engine_presumido.py`, `test_engine_real.py` |
| AT-116 inelegível | #8, #18 | `test_engine_eligibility.py` |
| AT-117 indeterminado | Decision 3, #18 | `test_engine_eligibility.py` |
| AT-118 regra ausente | Decision 2, #14, #23 | `test_engine_calculate.py` |
| AT-119 encargos por regime | #7, #19 | `test_engine_payroll_assumptions.py` |
| AT-120 memória completa | Pattern 1, #13 | `test_engine_calculate.py` |
| AT-121 idempotência | Decision 5, Pattern 5 | `test_engine_calculate.py`, `test_motor_pipeline.py` |
| AT-122 nova simulação | Decision 5 | `test_motor_pipeline.py` |
| AT-123 comparativo ordenado | #23, #44 | `test_engine_calculate.py` |
| AT-124 RLS | #1 | `motor.test.sql` |
| AT-125 ≤ 60 s | #26 | `test_motor_pipeline.py` |
| AT-126 golden 08/2026 aprovado | Decision 4, #35 | `test_engine_calculate.py` |
| SHOULD exportar XLSX | #25, #47 | `test_motor_pipeline.py` |
| Verify Gate | `scripts/verify.mjs` (inalterado) | `npm run verify` exit 0 |

---

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Repartição dos anexos transcrita errada | DAS errado para outros anexos/faixas | Transcrever da LC 123 com fonte; `verificado` por faixa; alerta na memória para regra não verificada; golden só cobre Anexo I | Médio até revisão contábil |
| A-001 a A-003 (faixa 5, LC 224 trimestral, hospitalar) incorretas | Valores divergentes | Regras isoladas por arquivo e marcadas `verificado: false`; troca = nova versão | Médio |
| Reclassificação do lucro para o Real mal parametrizada | Real subestimado ou superestimado | Linhas explícitas `real.reclassificacao`; golden 08/2026 aprovado pelo usuário | Baixo após aprovação |
| Mapeamento de atividades do PGDAS-D incompleto | Premissas pendentes demais | Sem padrão → premissa pendente para o analista escolher o perfil | Baixo |
| Amostra com uma única competência completa | Pouca cobertura de trimestres | Casos sintéticos nos testes (trimestre completo, LC 224, prejuízo) | Médio |
| Aprovação do golden depende do usuário | Build bloqueado em AT-126 | Memória de 08/2026 apresentada no Build em formato legível | Baixo |

---

## Advisor Ledger

None — no formal external design review.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-24 | SDD Design by RDD | Initial version |

---

## Next Step

Execute o **SDD Build by RDD**.
