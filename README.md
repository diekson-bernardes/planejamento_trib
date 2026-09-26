# Planejamento Tributário — Importação e Conciliação (ciclo 1), Motor Tributário (ciclo 2) e Decisão (ciclo 3)

Aplicativo web SaaS multi-escritório que importa PDFs do **PGDAS-D** e dos relatórios **Alterdata**
(Resumo Geral da Folha, DRE e Balancete Analítico), extrai todas as linhas com página e posição de
origem, concilia as fontes por competência (regras R1–R6), permite revisão com ajustes justificados e
**homologa** um snapshot imutável (SHA-256) exportável em JSON e XLSX.

Especificação: [`sdd/`](sdd/) (Brainstorm → Define → Design → Build). Base de conhecimento: [`kb/`](kb/).

## Arquitetura

| Parte | Pasta | Tecnologia |
|---|---|---|
| Site | `apps/web` | Next.js 16 (App Router), TypeScript, Tailwind v4, `@supabase/ssr` |
| Banco, Auth, Storage | `supabase/` | Postgres 17 com RLS por escritório, Storage privado, pgTAP |
| Worker | `services/worker` | Python 3.12+, `pdfplumber`, `psycopg`, `openpyxl` (container Docker) |

Fluxo: upload direto do navegador ao Storage → `source_files` → fila `jobs` → worker (classifica,
extrai, valida, concilia) → revisão/ajuste → `homologate_case()` → snapshot → exportação.

## Motor tributário (ciclo 2)

A partir de um dossiê **homologado**, a tela **Planejamento** (`/cases/<id>/planning`):

1. **Gera premissas sugeridas** (job `suggest_assumptions`) para o que os documentos não trazem — perfil de cada
   atividade do PGDAS-D, ICMS/ISS no regime normal, créditos de PIS/Cofins, ajustes do Real, encargos da folha e
   declarações de elegibilidade —, cada uma com a origem.
2. O analista **confirma ou altera** cada premissa (`confirm_assumption`; alteração exige justificativa, auditada).
3. **Calcula** (job `calculate`) elegibilidade + Simples (mensal) + Presumido e Real (IRPJ/CSLL trimestrais) nas
   competências com os quatro documentos. Mesmo snapshot + premissas + regras = mesma simulação (idempotente).
4. Mostra o **comparativo** ordenado por custo entre os elegíveis (sem recomendação) e a **memória de cálculo**
   linha a linha (regra@versão e origem); exporta XLSX (job `export_simulation`).

Regras versionadas em `services/worker/rules/2026/` (JSON, com `fonte` e `verificado`); a versão e o hash das
regras ficam gravados em cada simulação. Mudança de regra = nova versão no `manifest.json`. As tabelas do Simples
(Anexos I–V) foram transcritas do DOU de 28/10/2016 (LC 155/2016); regras marcadas `verificado: false` aparecem
com alerta na memória até a revisão contábil. Casos dourados: DAS de 06–08/2026 igual ao PGDAS-D, exemplos da
`kb/` e `services/worker/tests/golden/motor_202608.json` (aprovado pelo responsável de negócio).

## Decisão tributária (ciclo 3)

Na mesma tela de planejamento, **Projetar 2026** (job `project`) monta o exercício inteiro e roda o motor do ciclo 2
sem alteração sobre um snapshot sintético:

- **meses realizados** (competências completas) entram exatamente como homologados;
- **meses estimados** (antes do primeiro completo): receita pelas séries do PGDAS-D; lucro, créditos, ICMS/ISS e
  outras receitas em proporção à receita dos meses completos;
- **meses projetados** (depois do último completo): média simples, ou o **orçamento** informado nas premissas
  `projecao.receita`, `projecao.margem` e `projecao.folha` (alteração com justificativa, como qualquer premissa).

Em seguida:

1. **Sensibilidade** (grade de 11 pontos + bisseção) para receita, margem, folha, créditos de PIS/Cofins e ICMS/ISS:
   ponto de virada (ou "sem virada"), novo líder, distância, robustez e **limite jurídico** quando a elegibilidade muda.
2. **Recomendação**: `recomendado` (diferença ≥ limiar do escritório, padrão 5%), `inconclusivo` (abaixo) ou `bloqueado`
   (premissa pendente ou dado crítico ausente, com prévia). Mostra fatores, economia vs. segundo colocado e vs. regime
   atual, carga consumo/renda/folha e o custo de conformidade (exibido à parte, fora do ranking).
3. **Fluxo**: rascunho → em revisão → aprovada → emitida. Só o **responsável técnico** (marcado pelo admin com nome e
   CRC) aprova, e nunca a própria elaboração; devolução exige comentário; premissa alterada devolve para rascunho.
4. **PDF executivo** (job `emit_report`, ReportLab em modo reprodutível) no formato do SPTE + seções do PRD, gravado em
   `<escritório>/<dossiê>/reports/` com SHA-256; a recomendação emitida é imutável.

A política de decisão (intervalos, robustez, limiar padrão, grupos de carga, ressalvas) fica em
`services/worker/rules/decisao.json`, com versão e hash próprios gravados em cada projeção — separada das regras
tributárias. Golden: `services/worker/tests/golden/decisao_2026.json` (aprovado pelo responsável de negócio).

## Reforma Tributária 2027 (ciclo 4)

- **Regras por exercício**: `services/worker/rules/2027/` (versão `2027.1.0`, `verificado: false`) com CBS/IBS no lugar
  de PIS/Cofins (crédito financeiro sobre a base de créditos, saldo credor transportado), IPI zero e a base sem
  ICMS/ISS; as regras de 2026 e seus goldens não mudam.
- **Quatro alternativas** em 2027: Simples (CBS/IBS por dentro do DAS), **Simples híbrido** (CBS/IBS fora do DAS, pelo
  regime regular), Presumido e Real.
- **Premissas do grupo `reforma_2027`**: alíquotas de CBS e IBS (sem padrão — informadas pelo escritório), crescimento
  sobre 2026 e base de créditos por competência (sugerida pelos CFOPs creditáveis do Livro de Apuração ou pelas contas
  do balancete). Pendentes, **só bloqueiam a projeção de 2027** — cálculo e projeção de 2026 seguem liberados.
- **Projetar 2027** (`request_projection(case, 2027)`): a projeção de 2026 deslocada com o crescimento, sensibilidade com
  a variável "alíquota da CBS" (`rules/decisao_2027.json`) e o mesmo fluxo de aprovação e PDF.
- **Livro de Apuração do ICMS (Alterdata)**: documento opcional antes da homologação; entradas/saídas por CFOP conferidas
  com os totais e conciliação **R7** (compras CFOP 1102/2102/1403/2403 × débito da conta 13101 do balancete, alvo
  `compras_mercadorias` no mapeamento do escritório).
- Fora deste ciclo: mix de vendas (B2B × consumidor final), transição 2029–2033, Imposto Seletivo, ZFM, alíquotas por
  NCM, split payment e a opção semestral do híbrido.

## Pré-requisitos

- Node.js 20+ e npm
- Python 3.12+
- **Docker Desktop em execução** (o Supabase local roda em containers)
- Supabase CLI: instalada pelo `npm install` (devDependency). Use sempre `npx supabase …` — não é preciso instalação global.

## Configuração local

```bash
npm install
python -m pip install -e "services/worker[dev]"
npm run db:start
```

`npm run db:start` aplica as migrations e o `supabase/seed.sql` (dados fictícios). Depois:

1. Rode `npx supabase status` e copie `API_URL`, `ANON_KEY` e `SERVICE_ROLE_KEY`.
2. Crie `apps/web/.env.local` com `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` e `SUPABASE_SERVICE_ROLE_KEY` (modelo em `.env.example`).
3. Para o worker, exporte `DATABASE_URL`, `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`.

Usuários do seed (senha `senha-local-123`): `admin.a@example.com` (admin do Escritório A),
`analista.a@example.com` (analista do A), `analista.b@example.com` (analista do B).

```bash
npm run dev:web
npm run dev:worker
```

Site em http://localhost:3000; e-mails de convite locais em http://127.0.0.1:54324 (Mailpit).

## Verify Gate

```bash
npm run verify
```

Executa, e só passa (exit 0) se tudo passar:

1. checagem das amostras em `SAMPLES_DIR`, do Docker Engine e do Supabase local;
2. `pytest` do worker (golden das 6 amostras, validações, conciliação, pipeline com Postgres, desempenho ≤ 5 min,
   motor tributário: DAS = PGDAS-D, casos dourados de Presumido/Real, fluxo de planejamento ≤ 60 s);
3. `npx supabase test db` (pgTAP: isolamento RLS entre escritórios, homologação e planejamento);
4. typecheck e vitest do site.

### Amostras e LGPD

Os PDFs reais contêm CPF, RG e nomes, por isso **ficam fora do Git** (`docs/Amostras/` está no
`.gitignore`). Os testes leem os PDFs de `SAMPLES_DIR` (padrão `docs/Amostras`) e comparam com
`services/worker/tests/golden/*.json`, que contêm só campos, códigos e valores, sem dados pessoais.
Logs do worker registram apenas IDs e códigos de erro.

## Deploy (fora deste ciclo)

- Worker: `docker build -t planejamento-worker services/worker`, configurado só por variáveis de ambiente.
- Site: `npm run build --workspace apps/web` e `next start` em qualquer host Node.
- Banco: `npx supabase link` + `npx supabase db push` para o projeto remoto.
