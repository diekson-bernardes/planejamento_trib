# HANDOFF: Decisão Tributária (ciclo 3 do Planejamento Tributário)

> Registro do que ficou pronto e do que vem depois. Um arquivo por feature — cada etapa nova entra como seção no topo, nunca como arquivo separado.

## Ficha da feature

| Campo | Valor |
|---|---|
| **Objetivo** | Sobre o snapshot homologado, projetar o exercício de 2026 pelo motor do ciclo 2 (meses realizados, estimados e projetados), medir a sensibilidade de 5 variáveis com ponto de virada, emitir uma recomendação explicável (recomendado / inconclusivo / bloqueado) aprovada pelo responsável técnico e gerar o PDF executivo imutável. |
| **Status** | 🔨 em andamento |
| **Feito** | Brainstorm, Define e Design (2026-09-25); Build completo com Verify Gate verde, revisão pós-build com 5 correções aplicadas e golden `decisao_2026.json` aprovado (2026-09-25) |
| **Falta** | Merge do PR do ciclo 3 na `master` (código commitado e enviado); conferência visual das telas pelo usuário; revisão contábil das regras `verificado: false` e da política de decisão antes do piloto |
| **Pronto quando** | (1) `npm run verify` termina com exit 0 na `master` com o ciclo 3 incorporado; (2) pela interface em http://localhost:3000, um analista projeta 2026 num dossiê homologado, envia para revisão, um responsável técnico (marcado em /admin com nome e CRC) aprova, o PDF é emitido e baixado com o SHA-256 exibido na tela; (3) a projeção da amostra reproduz o golden aprovado (Simples R$ 387.997,75 < Presumido R$ 410.946,48 < Real R$ 1.201.374,01; recomendado Simples, 5,91%). |

---

## Eventos

- 2026-09-25 — Recorte do ciclo 3 no Brainstorm: **decisão completa** (projeção, sensibilidade, recomendação, fluxo de aprovação, PDF). Fora: sazonalidade, cenários conservador/base/expansão, variáveis de mix/B2B-B2C/benefícios, fluxo de caixa após tributos, assinatura eletrônica, RF-14/RF-15 e projeção de 2027 (Reforma).
- 2026-09-25 — Horizonte: exercício 2026 com orçamento opcional (2027 exige regras da Reforma ainda não parametrizadas). Amostra de referência alterada pelo usuário de "modelo de parecer" para "SPTE como referência de formato".
- 2026-09-25 — Define: limite de 60 s; golden da Projeção 2026 aprovado pelo usuário no build; o admin configura limiar e responsável técnico, que pode elaborar mas não aprova a própria elaboração.
- 2026-09-25 — Design: PDF com ReportLab (modo reprodutível); política de decisão em `services/worker/rules/decisao.json`, com versão e hash próprios, fora do hash das regras 2026.
- 2026-09-25 — Código do ciclo 3 commitado em `feat/decisao-tributaria` e PR aberto para a `master` a pedido do usuário.
- 2026-09-25 — Build: `request_projection` aceita premissas pendentes e gera prévia bloqueada (DEFINE AT-211 prevaleceu sobre o Design); tipo de premissa `ratio` (margem com sinal) acrescentado.

---

## 2026-09-25 — Build (SDD Build by RDD) e fechamento do ciclo 3

### O que foi feito

- **Motor de decisão** em `services/worker/src/worker/engine/`:
  - `projection.py`: snapshot sintético jan–dez/2026 lido pelo motor sem alteração. Meses realizados são copiados; estimados usam receita das séries do PGDAS-D e o resto proporcional à receita; projetados usam a média ou o orçamento `projecao.*`.
  - `sensitivity.py`: grade de 11 pontos + bisseção; ponto de virada, distância, robustez e limite jurídico.
  - `recommendation.py`: estados, texto, 3 fatores, economia, carga e conformidade à parte.
  - `decision.py`: orquestração + `result_hash`.
  - `decision_params.py`: carregador de `rules/decisao.json`.
- **Premissas novas** em `assumptions.py`: `projecao.receita`, `projecao.margem` (tipo `ratio`) e `projecao.folha` por mês de set–dez; `conformidade.custo_anual` por regime.
- **PDF** em `services/worker/src/worker/report_pdf.py`: formato do SPTE mais as seções do PRD, SHA-256 reprodutível.
- **Worker:** jobs `project` e `emit_report` em `pipeline.py` e `db.py`. PDF gravado em `<office>/<case>/reports/<rec>.pdf`.
- **Banco** (`supabase/migrations/20260925000003_decisao.sql`):
  - tabelas `projections` e `projection_lines` (append-only), `recommendations` (estado do fluxo) e `recommendation_events` (append-only);
  - responsável técnico em `office_members` (`is_technical_responsible`, `professional_name`, `crc`);
  - limiar em `offices.settings.decision_threshold`;
  - RPCs `set_technical_responsible`, `set_decision_threshold`, `request_projection`, `submit_recommendation`, `approve_recommendation`, `return_recommendation` e `request_report`;
  - gatilho que devolve a recomendação para rascunho quando uma premissa é confirmada, volta a pendente ou é removida;
  - Storage bloqueia gravação de usuários em `/reports/`.
- **Web:**
  - `/cases/[id]/planning`: botão "Projetar 2026" e lista de projeções;
  - `/cases/[id]/planning/projection/[projId]`: recomendação, fluxo, comparativo, sensibilidade e mensal por regime;
  - `/admin`: limiar e responsável técnico;
  - `/api/reports/[id]`: download do PDF por URL assinada.
- **Revisão pós-build (5 aplicadas):**
  - chave do job de emissão por pedido;
  - base da sensibilidade no mesmo eixo dos demais pontos;
  - virada só com o mesmo conjunto elegível do base;
  - reset da recomendação em pendente e remoção;
  - limiar legível só por membros.
- **Evidência:**
  - `npm run verify` PASS (pytest 161, pgTAP 94, typecheck, vitest 17);
  - `next build` ok; imagem Docker com ReportLab 5.0.1;
  - smoke E2E: projeção em 4,1 s igual ao golden, PDF com SHA-256 conferido, escritório B vê 0/0.
- **Relatório:** `sdd/BUILD_REPORT_DECISAO_TRIBUTARIA.md` (validado).

### Casos e testes em aberto

- **Golden aprovado** — `services/worker/tests/golden/decisao_2026.json` (Diekson Bernardes, 2026-09-25):
  - receita anual projetada R$ 3.501.301,63, margem 80,4% (DREs sem CMV);
  - recomendado Simples, R$ 22.948,73 (5,91%) abaixo do Presumido;
  - viradas: receita +9,7% → Presumido (atenção), limite jurídico em +37%; folha −19% → Presumido (atenção); ICMS/ISS −30% → Presumido (robusta); margem 10,8% → Real (robusta); créditos sem virada.
- **Dossiê do smoke** — `55e52405-4086-4a90-9b89-04aa808b42da`, escritório A `a0000000-0000-4000-8000-000000000001`, empresa CNPJ 37.704.456/0001-42, 12 PDFs de 06–08/2026:
  - projeção `1fbf35c0-7d0c-405b-bb50-030e32513846`;
  - recomendação emitida `4960a252-1b2f-4557-adb7-12adec5f24cb`;
  - as divergências R5 de 06 e 07/2026 foram justificadas no smoke.
- **Marcação local do responsável técnico** — o smoke marcou `admin.a@example.com` (usuário do seed `a1111111-1111-4111-8111-111111111111`) como responsável técnico, com nome "Responsável Técnico (smoke)" e CRC fictício `SP-000000/O-0`.
- **Dossiês do usuário no ambiente local** — `003b9273-0d65-494c-b8ac-c15384ca72a8` e `4eb5545b-9f95-46a0-8bdb-f2420e66ff5b` (07–08/2026) não foram tocados pelo ciclo 3.

### Pendências

**🐛 Bug fix** — o que ficou quebrado, parcial ou com comportamento errado conhecido:

- nenhuma conhecida após a revisão pós-build.
- Risco aceito: a margem da amostra (≈ 80%) vem de DREs sem CMV; a recomendação da amostra depende dessa característica do dado.

**✨ Feature improvement** — o que é incremento planejado, melhoria ou próxima etapa de escopo:

- **Commit e PR:** fazer o commit do código do ciclo 3 em `feat/decisao-tributaria` e abrir o PR para a `master`.
- **Revisão contábil da política de decisão** (`rules/decisao.json`): intervalos da sensibilidade (A-205), faixas de robustez (A-204) e textos de ressalva.
- **Revisão contábil das regras `verificado: false`** (LC 224 trimestral, faixa 6, hospitalar, encargos, elegibilidade, atividades).
- **Documentos de 09/2026:** com eles o 2026-T3 fecha; o golden `decisao_2026` mudaria e exigiria nova aprovação.
- **Itens cortados por YAGNI:** sazonalidade, cenários, variáveis de mix/B2B-B2C/benefícios, fluxo de caixa, assinatura eletrônica, RF-14/RF-15.
- **Projeção de 2027:** exige parametrizar as regras da Reforma (CBS/IBS) como nova versão de regras.

### Checklist de fechamento (inventário do que foi conferido)

- **O código roda?** O worker está em segundo plano (`python -m worker.main`, `WORKER_POLL_SECONDS=1`) e o Next.js em http://localhost:3000. O smoke E2E percorreu projeção → aprovação → PDF.
- **Os critérios de aceite passam?** AT-201 a AT-223 têm evidência no Build Report, e `npm run verify` terminou com exit 0.
- **As mudanças estão salvas onde deveriam?** Sim: commitadas na branch `feat/decisao-tributaria`, enviadas ao `origin` e com PR aberto para a `master`.
- **O que quebrou está anotado?** Sim: nas Pendências acima e em "Issues Encountered" do Build Report.
- **Telas:** a conferência visual não foi feita por mim. O navegador embutido estava deslogado e eu não digito senhas; o HTML autenticado das páginas foi validado.

### Próximos passos

1. **Conferir as telas** — http://localhost:3000/cases/55e52405-4086-4a90-9b89-04aa808b42da/planning/projection/1fbf35c0-7d0c-405b-bb50-030e32513846 e http://localhost:3000/admin (login com `analista.a@example.com` e `admin.a@example.com`). Pronto quando: o usuário aprovar ou listar ajustes.
2. **Revisar e fazer o merge do PR** `feat/decisao-tributaria` → `master` em https://github.com/diekson-bernardes/planejamento_trib. Pronto quando: PR merged pelo usuário e branch apagada.
3. **Agendar a revisão contábil** de `services/worker/rules/decisao.json` e das regras `verificado: false`. Pronto quando: nova versão publicada (ex.: `decisao` 2026.1.1) e goldens reaprovados se os valores mudarem.
4. **Próximo ciclo** (regras de 2027/Reforma ou itens cortados por YAGNI) começa pela skill **sdd-brainstorm**. Pronto quando: existir o Brainstorm aprovado do novo ciclo.

### Alertas — o que não quebrar

- **Motor intocado:** a projeção reutiliza o motor do ciclo 2 via snapshot sintético; não alterar o motor para acomodar a projeção. Os goldens `motor_202608` e `motor_202606_08` devem continuar exatos.
- **Política de decisão separada:** `rules/decisao.json` tem versão e hash próprios. Mudar a política = nova versão, sem tocar o hash das regras tributárias 2026.
- **Aprovação:** só o responsável técnico aprova, e nunca a própria elaboração. A recomendação emitida e o PDF são imutáveis; premissa confirmada, voltada a pendente ou removida devolve a recomendação aprovada para rascunho.
- **Custo de conformidade** nunca entra no ranking.
- **Verify Gate:** parar o worker em segundo plano antes de `npm run verify`, porque ele disputa os jobs dos testes de integração.
- **Segurança e dados:**
  - amostras reais em `docs/Amostras/` contêm CPF/RG e nunca vão para o Git;
  - logs só com IDs e códigos;
  - `SUPABASE_SERVICE_ROLE_KEY` só no servidor;
  - a IA não digita senhas no navegador.
- **Fora de escopo:** projeção de 2027, sazonalidade, cenários, assinatura eletrônica, RF-14/RF-15, fluxo de caixa após tributos.

### Onde está o trabalho

- **Projeto:** `C:\Users\User\Documents\BRAVO-BUILDER-PROJETOS\PLANEJAMENTO_TRIB`.
- **Git:** branch `feat/decisao-tributaria` (a partir da `master` `3388298`) com `a4265e7` (documentos) e o commit do código do ciclo 3, enviada ao `origin` = https://github.com/diekson-bernardes/planejamento_trib.git, com PR aberto para a `master` (branch padrão).
- **Artefatos SDD:**
  - `sdd/BRAINSTORM_DECISAO_TRIBUTARIA.md`;
  - `sdd/DEFINE_DECISAO_TRIBUTARIA.md`;
  - `sdd/DESIGN_DECISAO_TRIBUTARIA.md`;
  - `sdd/BUILD_REPORT_DECISAO_TRIBUTARIA.md`;
  - ciclos anteriores em `sdd/HANDOFF_IMPORTACAO_CONCILIACAO.md` e `sdd/HANDOFF_MOTOR_TRIBUTARIO.md`.
- **Ambiente local:**
  - Docker Desktop e `npx supabase start` (Postgres em `127.0.0.1:54322`, API em `127.0.0.1:54321`);
  - Next.js na porta 3000;
  - worker via `python -m worker.main` com `PYTHONPATH=services\worker\src` e as variáveis de `npx supabase status -o json`.
