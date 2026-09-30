# HANDOFF: Atividades mistas e Fator R no Planejamento Rápido (ciclo 6)

> Registro do que ficou pronto e do que vem depois. Um arquivo por feature — cada etapa nova entra como seção no topo, nunca como arquivo separado.

## Ficha da feature

| Campo | Valor |
|---|---|
| **Objetivo** | No dossiê rápido, dividir o faturamento entre várias atividades (CNAEs) por percentual e calcular o Fator R mês a mês com a folha real dos 12 meses anteriores, com escolha explícita para meses sem folha e simulação informativa da "folha ideal". |
| **Status** | 🔨 em andamento (build completo e commitado; falta push, PR e merge) |
| **Feito** | Brainstorm, Define, Design e Build em 2026-09-28; Verify Gate verde e commit `bf84638` em 2026-09-30 |
| **Falta** | Push da branch `feat/atividades-fator-r`, PR (aberto pelo usuário, sem `gh` na máquina) e merge na `master` |
| **Pronto quando** | O commit `bf84638` estiver na `origin/master` (conferir com `git merge-base --is-ancestor bf84638 origin/master`) e `npm run verify` terminar com `VERIFY GATE: PASS` na `master` |

---

## Eventos

- 2026-09-28 — Ciclo 6 escolhido no brainstorm: precisão do Planejamento Rápido, com foco em atividades mistas e Fator R (opções a e b). Produção, mix B2B e novas entradas ficaram para ciclos futuros.
- 2026-09-28 — Define: folha do Fator R = salários + pró-labore + FGTS 8% (só no rápido); folha ideal mostra pró-labore e salário lado a lado; soma dos percentuais exatamente 100,00%.
- 2026-09-28 — Golden `rapido_misto_2027` aprovado pelo usuário (Diekson Bernardes).
- 2026-09-30 — 1º `npm run verify` vermelho por `rls.test.sql` #22 (tolerância do Escritório A alterada para R$ 10 pela tela em 2026-09-29 02:20 UTC); teste corrigido para fixar a tolerância na transação; 3ª execução verde.

---

## 2026-09-30 — Build do ciclo 6 concluído e commitado

### O que foi feito

- **Banco** — `supabase/migrations/20260929000008_atividades_fator_r.sql`:
  - tabela `case_activities` (cnae, descricao, percentual numeric(5,2), origem), com RLS `is_member`, trigger `tg_block_if_homologated` e FK em cascata;
  - RPC `set_case_activities(p_case_id, p_items jsonb)`: substitui o conjunto; exige CNAE de 7 dígitos, sem repetição; soma exata de 100 com mais de uma atividade; atividade única = 100%;
  - `rapido_blockers` bloqueia soma ≠ 100; `homologate_case` grava `content.activities` no snapshot.
  - As duas funções foram alteradas por substituição de trecho, com guarda que falha se o trecho não for encontrado.
- **Worker:**
  - `engine/fator_r.py` (novo): folha do mês = salários × 1,08 + pró-labore; linha do tempo da folha; `folha_12m` por competência; `FolhaIncompletaError`; `make_adjuster`; `folha_ideal_lines`.
  - `rules/fator_r.json`: FGTS 0,08, INSS do sócio 0,11, provisões 0,1944, `verificado: false`, hash próprio (não muda o hash das regras 2026/2027).
  - `engine/quick_view.py`: N atividades × variantes (normal/ST/mono); ST/mono retirados só das atividades Anexo I/II; perfil sugerido por CNAE; sugestão `rapido.folha_incompleta` (choice `media`/`zero`) só quando falta folha e há Fator R; a sugestão antiga "média × 12" saiu.
  - `engine/projection.py`: `ProjectedCase.payroll_history`.
  - `engine/decision.py`: `project(..., adjust=None)`, aplicado também nos cenários de sensibilidade.
  - `pipeline.py`: liga o ajuste e grava as linhas da folha ideal.
  - `report_pdf.py` + `db.py`: seções "Atividades da empresa", "Fator R mês a mês" e "Folha ideal".
- **Web:**
  - `CaseActivities.tsx`: marcar atividades, percentuais, soma ao vivo, incluir CNAE manual; botão bloqueado se a soma ≠ 100,00%.
  - `saveActivities` em `cases/actions.ts`; `activitiesSchema` + `percentToCents` em `lib/schemas.ts`.
  - `FatorRTable.tsx` e `FolhaIdealTable.tsx`, mais a tabela de atividades na tela da projeção.
  - Rótulos novos em `format.ts`.
- **Testes:**
  - `supabase/tests/atividades_fator_r.test.sql` (19 asserts);
  - `services/worker/tests/test_fator_r.py` (13 testes: unidade, golden e integração com Postgres, incluindo o PDF);
  - golden `services/worker/tests/golden/rapido_misto_2027.json`;
  - caso fictício `misto_content()` em `tests/conftest.py`;
  - casos novos em `apps/web/src/lib/schemas.test.ts`.
- **Verify Gate** (`npm run verify`): pytest 236 passed (260 s) · pgTAP Files=9, Tests=169, PASS · typecheck ok · vitest 28 passed · `VERIFY GATE: PASS`.
- **Documentos:** `sdd/BRAINSTORM_ATIVIDADES_FATOR_R.md`, `sdd/DEFINE_ATIVIDADES_FATOR_R.md`, `sdd/DESIGN_ATIVIDADES_FATOR_R.md`, `sdd/BUILD_REPORT_ATIVIDADES_FATOR_R.md` (validado).

**Checklist de fechamento (inventário do que foi conferido):**
- **Código roda:** `npm run verify` verde em 2026-09-30, e smoke completo pela tela no navegador interno.
- **Critérios de aceite:** AT-601 a AT-617 do DEFINE com evidência no BUILD_REPORT.
- **Mudanças salvas:** commit `bf84638` na branch local `feat/atividades-fator-r`; ainda não enviado ao GitHub.
- **O que quebrou está anotado:** falha do `rls.test.sql` (corrigida) e desvios técnicos, registrados no BUILD_REPORT.

### Casos e testes em aberto

- **Golden aprovado `rapido_misto_2027`** (fictício): comércio 4744-0/01 com 60% e software 6201-5/01 com 40%.
  - Faturamento 150.000 + 2.500/mês de 09/2025 a 08/2026.
  - Salários 12.000 + 2.800/mês, pró-labore 6.000.
  - DRE só de 06 a 08/2026.
  - Resultado:
    - Fator R de 01/2027 = 529.920,00 ÷ 2.050.000,00 = 25,85% (Anexo V);
    - Anexo V de 01 a 03/2027 e III de 04/2027 em diante;
    - totais 2027: Simples 270.536,41 · Simples híbrido 390.701,28 · Presumido 474.240,64.
- **Dossiê de smoke** no Escritório A (teste) (`a0000000-0000-4000-8000-000000000001`):
  - caso `d6000000-0000-4000-8000-000000000006`, empresa `c6000000-0000-4000-8000-000000000006`, "Smoke Ciclo 6 Comércio e Software Ltda (fictícia)", CNPJ 11.444.777/0001-61;
  - homologado; projeção 2027 `fee016f5-2aac-40bd-b1fa-e228894a0fc1` com os mesmos números do golden.
  - Pode ser excluído pela tela (Dossiês → Excluir) quando não for mais útil.
- **Tolerância do Escritório A** está em R$ 10 (mudança feita pela tela, não pelo build); os testes não dependem mais dela.

### Pendências

**🐛 Bug fix** — o que ficou quebrado, parcial ou com comportamento errado conhecido:

- nenhuma

**✨ Feature improvement** — o que é incremento planejado, melhoria ou próxima etapa de escopo:

- Push, PR e merge do ciclo 6 (branch `feat/atividades-fator-r`, commit `bf84638`).
- Revisão contábil de `services/worker/rules/fator_r.json` (FGTS 8%, INSS do sócio 11%, provisões 19,44%) — marcados `verificado: false`.
- Revisão contábil da tabela `services/worker/rules/cnae_anexos.json` e das regras 2027 (pendência dos ciclos 4 e 5).
- A economia da folha ideal é aproximação (receita da atividade × diferença de alíquota efetiva V − III, sem refazer faixas); a fórmula está na origem da linha.
- Linhas `fator_r` saem repetidas para as variantes ST/mono da mesma atividade (receita zero); tela e PDF deduplicam por mês.
- Sazonalidade por atividade, leitura da divisão por atividade em PDF, IRRF do pró-labore e atividades mistas no dossiê completo ficaram fora (YAGNI).
- Pendências antigas: token na automação n8n de consulta de CNPJ; reavaliar "qualquer membro exclui dossiê homologado"; `sdd/HANDOFF_PLANEJAMENTO_RAPIDO.md` ainda diz que PR/merge estão pendentes.

### Próximos passos

1. Enviar a branch — `git push -u origin feat/atividades-fator-r`. Pronto quando: `git branch -r` listar `origin/feat/atividades-fator-r`.
2. Abrir o PR pelo usuário (não há `gh` instalado) — link https://github.com/diekson-bernardes/planejamento_trib/compare/master...feat/atividades-fator-r?expand=1, título `feat: ciclo 6 — atividades mistas e Fator R mês a mês no Planejamento Rápido`; o corpo termina com "🤖 Generated with [Claude Code](https://claude.com/claude-code)". Pronto quando: o PR existir na lista de pull requests do repositório.
3. Após o usuário avisar o merge — `git fetch origin && git merge-base --is-ancestor bf84638 origin/master && echo MERGED`; só então `git checkout master && git pull origin master && git branch -d feat/atividades-fator-r && git push origin --delete feat/atividades-fator-r`. Pronto quando: `MERGED` impresso e a branch sumir de `git branch -a`.
4. Iniciar o próximo ciclo com a skill `sdd-brainstorm` — candidatos já levantados: produção (hospedagem, backups, token no n8n), mix B2B da Reforma, novas entradas (XML de NF-e, SPED). Pronto quando: `sdd/BRAINSTORM_*.md` do ciclo 7 gerado.

### Alertas — o que não quebrar

- Goldens exatos: `motor_202608`, `motor_202606_08`, `decisao_2026`, `decisao_2027`, `rapido_2027` e agora `rapido_misto_2027`.
  - Hash das regras: 2026 `e00eaa79e1ae`; 2027.1.0 `e60103aefe5e`.
  - `fator_r.json` e `cnae_anexos.json` têm hash próprio e não entram no hash das regras.
- Dossiê rápido sem atividades gravadas = CNAE principal com 100% (dossiês do ciclo 5 continuam iguais).
- A folha do Fator R do rápido é derivada, nunca premissa editável; o dossiê completo continua usando a série 2.3 do PGDAS-D.
- Segurança:
  - nunca digitar senha no navegador;
  - `docs/Amostras` (PDFs reais) nunca no git;
  - goldens sem PII;
  - logs só com IDs e códigos;
  - `SUPABASE_SERVICE_ROLE_KEY` só no servidor;
  - `.env*` fora do git;
  - nada de sócios/QSA da consulta de CNPJ;
  - chamada real ao n8n só com autorização.
- Operação:
  - pare o worker (`npm run dev:worker`) antes de `npm run verify`, senão ele consome jobs dos testes;
  - aplique migrations com `npx supabase migration up` (nunca `db reset`, que apaga os dados do usuário).
- Commits terminam com "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"; o merge é feito pelo usuário.
- **Fora de escopo:** Lucro Real no rápido; percentual ST/mono por atividade; mudar a composição da folha do dossiê completo.

### Onde está o trabalho

- **Projeto:** `C:\Users\User\Documents\BRAVO-BUILDER-PROJETOS\PLANEJAMENTO_TRIB`.
- **Branch:** `feat/atividades-fator-r`, commit `bf84638` (não enviado).
- **Base:** `master` em `809be4b`.
- **Remoto:** https://github.com/diekson-bernardes/planejamento_trib.
- **Ambiente local:** Supabase local (Docker) com a migration `20260929000008` aplicada; worker rodando em segundo plano (`npm run dev:worker`); web em http://localhost:3000.
