# HANDOFF: Reforma Tributária 2027 (ciclo 4)

> Registro do que ficou pronto e do que vem depois. Um arquivo por feature — cada etapa nova entra como seção no topo, nunca como arquivo separado.

## Ficha da feature

| Campo | Valor |
|---|---|
| **Objetivo** | Comparar o exercício de 2027 sob as regras da Reforma (CBS/IBS no lugar de PIS/Cofins, crédito financeiro, IPI zero) em quatro alternativas — Simples por dentro, Simples híbrido, Presumido e Real — com recomendação aprovada pelo responsável técnico e PDF, sem alterar os resultados de 2026; o Livro de Apuração do ICMS entra como documento opcional com a conciliação R7. |
| **Status** | 🔨 em andamento (build completo; falta commit, PR e merge) |
| **Feito** | Brainstorm, Define e Design (2026-09-25, commit `302628c`); Build com Verify Gate verde, revisão pós-build aplicada e golden `decisao_2027` aprovado (2026-09-26) |
| **Falta** | Commit do build na branch `feat/reforma-2027`, push, PR para `master` e merge pelo usuário; revisão contábil das regras de 2027 (`verificado: false`) antes do uso com clientes |
| **Pronto quando** | O PR do ciclo 4 estiver merged na `master` com `npm run verify` = "VERIFY GATE: PASS" na branch (pytest 184, pgTAP 108, typecheck, vitest 19) |

---

## Eventos

- 2026-09-25 — Escopo cortado no Brainstorm: mix de vendas/B2B, transição 2029–2033, Imposto Seletivo, ZFM, alíquotas por NCM, split payment e opção semestral do híbrido ficam para um próximo ciclo (decisão do usuário).
- 2026-09-25 — Livro de Apuração do ICMS (Alterdata) adotado como fonte dos créditos em vez de "mix de compras" manual; documento opcional, antes da homologação (decisão do usuário no Define).
- 2026-09-26 — Durante o Build, a base de CBS/IBS passou a excluir o ICMS/ISS do regime (previsto no Design, faltava no código) e o golden foi apresentado já com essa correção; usuário aprovou.

---

## 2026-09-26 — Build do ciclo 4

### O que foi feito

- **Regras por exercício:** `services/worker/rules/2027/` (versão `2027.1.0`, hash `e60103aefe5e`, todos os arquivos com `verificado: false`) e `services/worker/rules/decisao_2027.json` (variável `cbs` em fração 0,5–1,5; carga de consumo com `cbs`/`ibs`). As regras de 2026 (hash `e00eaa79e1ae`) e `rules/decisao.json` não mudaram.
- **Motor:** `engine/cbs_ibs.py` (débito = (receita − monofásica − ICMS/ISS do regime − exclusões) × alíquota; crédito = `reforma.creditos_base` × alíquota + saldo credor transportado). Presumido, Real e Simples usam CBS/IBS quando `rules.consumo` existe; `SIMPLES_HIBRIDO` tira CBS/IBS do DAS e apura pelo regime regular.
- **Projeção 2027:** `shift_year` em `engine/projection.py` desloca a projeção de 2026 com `reforma.crescimento`; sensibilidade ganhou a variável "Alíquota da CBS"; `decision.project` bloqueia a recomendação quando falta alíquota.
- **Premissas `reforma_2027`:** `reforma.cbs_aliquota`, `reforma.ibs_aliquota` (sem padrão), `reforma.crescimento` (padrão 0), `reforma.creditos_base` por competência (sugerida pelos CFOPs 1102/2102/1403/2403/2353 do Livro, ou pelas contas de mercadorias do balancete) e `conformidade.custo_anual` do híbrido. Pendentes, só bloqueiam 2027 (`pipeline.blocking`, SQL `request_calculation`, gatilho de reset filtrado por `projections.year`).
- **Livro de Apuração:** `parsers/livro_icms_alterdata.py`, validações de soma, R7 (compras CFOP 1102/2102/1403/2403 × débito da conta 13101, alvo `compras_mercadorias`).
- **Banco:** `supabase/migrations/20260925000004_reforma_2027.sql` (já aplicada no banco local; a redefinição do gatilho foi aplicada à mão via `psql` no container `supabase_db_planejamento-trib`) e `supabase/tests/reforma_2027.test.sql` (14 asserts).
- **Web:** botão "Projetar 2027", pendências por exercício, tabelas com 4 regimes (`REGIME_ORDER`/`orderedRegimes` em `apps/web/src/lib/format.ts`), rótulos do Livro/R7/CBS/IBS, `projectionYearSchema`.
- **Golden aprovado:** `services/worker/tests/golden/decisao_2027.json` — aprovado por Diekson Bernardes em 2026-09-26 com CBS 9,5%, IBS 0,1%, crescimento 5%: Simples 378.692,23 < híbrido 471.845,47 < Presumido 475.153,57 < Real 1.260.440,27; recomendado Simples (24,60% abaixo do híbrido); viradas: receita +20,9% (Presumido), créditos +55% (híbrido).
- **Revisão pós-build:** 7 achados, todos corrigidos com teste (reset da recomendação de 2026 por premissa de 2027; dossiê sem alíquota recomendando Simples; base sem ICMS/ISS; créditos fixos sob a alavanca de receita; carga de consumo sem CBS/IBS; custo do híbrido bloqueando 2026; ordem do PDF).
- **Relatório:** `sdd/BUILD_REPORT_REFORMA_2027.md`; KB atualizada em `kb/reforma-tributaria/concepts/simples-na-reforma.md`; README com seção do ciclo 4.

### Casos e testes em aberto

- **Smoke do ciclo 4** no dossiê local `6c65265c-47d5-43e7-b1a8-4559cb5a5342` (escritório seed `a0000000-0000-4000-8000-000000000001`, CNPJ 37.704.456/0001-42): projeção 2027 `66fa9cac-89cc-47a4-ad1e-ff0c140a55cc`, recomendação `301c13ba-61f8-4147-9345-cb9208095c60` emitida (PDF 19.948 bytes). O `admin.a` do seed está marcado como responsável técnico com CRC fictício `SP-000000/O-0` (do smoke do ciclo 3).
- **Amostra nova:** `docs/Amostras/Livro Apuração ICMS 08.pdf` (fora do Git — contém dados reais) — 100 valores, entradas 158.503,98, saídas 205.577,54; R7 de 08/2026 = 149.985,71 dos dois lados.
- **Objetos órfãos no Storage local:** 13 PDFs do dossiê de smoke apagado `2c7f9b85-faac-43ed-a04e-02e75acca8f7` (caminho `a0000000-0000-4000-8000-000000000001/2c7f9b85-faac-43ed-a04e-02e75acca8f7/`), da primeira tentativa com o worker sem variáveis do Supabase.

### Checklist de fechamento (inventário)

- **O código roda?** `npm run verify` na branch terminou com "VERIFY GATE: PASS" (pytest 184 passed, pgTAP Files=5 Tests=108, typecheck, vitest 19); `next build` e `docker build` + `docker run` do worker concluídos; smoke E2E completo.
- **Os critérios de aceite passam?** AT-401 a AT-420 com evidência no `BUILD_REPORT_REFORMA_2027.md`; golden aprovado reproduzido por `test_projection_2027_matches_approved_golden`.
- **As mudanças estão salvas onde deveriam?** Estão no disco, na branch `feat/reforma-2027`, **sem commit** (só `302628c` com os documentos). Virou pendência.
- **O que quebrou está anotado?** Sim — nada quebrado conhecido; desvios e hipóteses em Pendências e no Build Report.

### Pendências

**🐛 Bug fix** — o que ficou quebrado, parcial ou com comportamento errado conhecido:

- nenhuma

**✨ Feature improvement** — o que é incremento planejado, melhoria ou próxima etapa de escopo:

- Commit, push e PR do ciclo 4 (o build está só no disco).
- Revisão contábil das regras de 2027 na LC 214/2025 oficial (hipótese A-401: repartição do DAS de 2027 com PIS+Cofins → CBS e IBS sem parcela; monofásico tratado como isento de CBS; ICMS/ISS fora da base pelo art. 12, § 2º) — correção vira versão `2027.x`.
- ICMS excluído da base de CBS/IBS pelo valor líquido do regime, não pelo destacado nas notas (risco aceito: CBS/IBS levemente superestimadas quando há crédito de ICMS). Candidato: usar a coluna "imposto" das saídas do Livro.
- Devoluções de venda (CFOP 1202/1411) não deduzidas da receita na base.
- SHOULD do Define não implementado: conferência informativa "saídas do Livro × receita do PGDAS-D".
- Próximo ciclo (cortes do Brainstorm): mix de vendas B2B × consumidor final, transição 2029–2033, Imposto Seletivo, ZFM, alíquotas por NCM, split payment, opção semestral do híbrido.
- Limpar os objetos órfãos do Storage local do dossiê `2c7f9b85-faac-43ed-a04e-02e75acca8f7` (opcional, só ambiente local).

### Próximos passos

1. Conferir a branch — `git status` em `C:\Users\User\Documents\BRAVO-BUILDER-PROJETOS\PLANEJAMENTO_TRIB` na branch `feat/reforma-2027`. Pronto quando: a lista bater com "Files Changed" do `sdd/BUILD_REPORT_REFORMA_2027.md` e `docs/Amostras/` e `.env*` não aparecerem.
2. Commitar o ciclo 4 — mensagem "feat: ciclo 4 — Reforma Tributária 2027 (CBS/IBS, Simples híbrido, Livro de Apuração e R7)" terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Pronto quando: `git status` limpo (exceto `.claude/`, se o usuário não quiser versioná-lo).
3. Push e PR para `master` em `https://github.com/diekson-bernardes/planejamento_trib`, corpo terminando com "🤖 Generated with [Claude Code](https://claude.com/claude-code)". Pronto quando: PR aberto e checks lidos.
4. Merge feito pelo usuário (nunca pelo agente). Pronto quando: PR merged na `master`.
5. Revisão contábil das regras 2027 com o responsável técnico — `services/worker/rules/2027/simples.json` e `consumo.json`. Pronto quando: cada ponto da hipótese A-401 confirmado ou corrigido em uma versão `2027.x` com golden reaprovado.

### Alertas — o que não quebrar

- Goldens exatos: `motor_202608`, `motor_202606_08`, `decisao_2026` e `decisao_2027` (este aprovado em 2026-09-26). Qualquer mudança de número exige nova aprovação do usuário.
- Nunca alterar `services/worker/rules/2026/` (hash `e00eaa79e1ae`) nem `rules/decisao.json`; mudança de regra = nova versão.
- O campo `unidade` da sensibilidade só aparece quando difere de "reais" — incluí-lo sempre muda os hashes das projeções de 2026.
- Premissas do grupo `reforma_2027` não podem bloquear o cálculo nem a projeção de 2026, nem devolver a rascunho uma recomendação de 2026.
- Parar o worker em segundo plano antes de `npm run verify` (disputa jobs dos testes). Para rodar o worker local: `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` de `npx supabase status -o env`.
- Segurança: não digitar senhas no navegador; `docs/Amostras` (CPF/RG) nunca vai para o Git; goldens sem dados pessoais; logs só com IDs; `SUPABASE_SERVICE_ROLE_KEY` só no servidor; `.env*` fora do Git; smoke só em dossiê próprio; merge é do usuário.
- **Fora de escopo:** mix de vendas, transição 2029–2033, IS, ZFM, NCM, split payment e opção semestral do híbrido.

### Onde está o trabalho

Projeto `C:\Users\User\Documents\BRAVO-BUILDER-PROJETOS\PLANEJAMENTO_TRIB`, branch `feat/reforma-2027` (a partir da `master` em `6f71835`), remoto `origin` = `https://github.com/diekson-bernardes/planejamento_trib.git`. Documentos do ciclo em `sdd/*_REFORMA_2027.md`. Supabase local (`npx supabase`) com a migration `20260925000004_reforma_2027.sql` aplicada.

---

## 2026-09-25 — Brainstorm, Define e Design

Brainstorm, Define (Clarity Score e Verify Gate = `npm run verify`, projeção ≤ 60 s, Livro antes da homologação) e Design (45 itens de manifest, regras por exercício, ADRs) gravados em `sdd/BRAINSTORM_REFORMA_2027.md`, `sdd/DEFINE_REFORMA_2027.md` e `sdd/DESIGN_REFORMA_2027.md`; commit `302628c` na branch `feat/reforma-2027`.
