# HANDOFF: Motor Tributário (ciclo 2 do Planejamento Tributário)

> Registro do que ficou pronto e do que vem depois. Um arquivo por feature — cada etapa nova entra como seção no topo, nunca como arquivo separado.

## Ficha da feature

| Campo | Valor |
|---|---|
| **Objetivo** | Sobre o snapshot homologado do ciclo 1, avaliar a elegibilidade e calcular Simples Nacional, Lucro Presumido e Lucro Real das competências completas, com premissas confirmadas pelo analista, regras versionadas (exercício 2026), memória de cálculo linha a linha e comparativo ordenado por custo entre os regimes elegíveis — sem recomendação (a recomendação é do ciclo 3). |
| **Status** | 🔨 em andamento |
| **Feito** | Brainstorm, Define e Design (2026-09-25); Build completo com Verify Gate verde, golden 08/2026 aprovado e revisão pós-build com 9 correções aplicadas e 1 contestada (2026-09-25) |
| **Falta** | Conferência visual das telas de planejamento pelo usuário; revisão contábil das regras marcadas `verificado: false` antes do piloto |
| **Pronto quando** | (1) `npm run verify` termina com exit 0 na `master`; (2) pela interface em http://localhost:3000/cases/<id>/planning, um analista gera premissas, confirma, calcula e vê o comparativo igual aos goldens aprovados (08/2026: Simples 23.430,47 < Presumido 26.165,68 < Real 63.093,28; 06–08/2026: Simples 99.249,46 < Presumido 102.578,12 < Real 299.770,55) e baixa o XLSX da memória; (3) o responsável técnico registra a revisão das regras `verificado: false` (LC 224 trimestral, ICMS/ISS da faixa 6 pela faixa 5, cumulatividade hospitalar). |

---

## Eventos

- 2026-09-25 — Ciclo 2 recortado no Brainstorm como **somente elegibilidade + cálculo dos três regimes + memória + comparativo**; projeção de 12 meses, sensibilidade, ponto de virada, recomendação/parecer, aprovação e PDF executivo ficam para o **ciclo 3**.
- 2026-09-25 — Cycle 1 commitado (`f6daf3c`) e criada a branch `feat/motor-tributario` antes do build; modo `default`; revisão escolhida "só após o build".
- 2026-09-25 — Golden `services/worker/tests/golden/motor_202608.json` aprovado pelo usuário ("sim"), com a ressalva de que a DRE da amostra não tem CMV.
- 2026-09-25 — Revisão pós-build: 9 correções aplicadas; a da LC 224 foi contestada por seguir a premissa A-002 do DEFINE. A identificação das atividades mudou, por isso os dossiês com premissas antigas precisam de "Regenerar premissas".
- 2026-09-25 — Ciclo 2 commitado e publicado: PR #1 (ciclo 1) e PR #2 (ciclo 2) merged na `master` de `https://github.com/diekson-bernardes/planejamento_trib`; `master` virou a branch padrão; branches de feature apagadas.
- 2026-09-25 — Revisão do Codex no PR #2: 3 correções aplicadas (premissas gravadas por simulação, PIS/Cofins zerados por tributo, base do Presumido ≥ 0) e 1 contestada (sublimite: efeito no mês seguinte ao excesso >20%).
- 2026-09-25 — Com DRE e balancete de 06 e 07 (amostras renomeadas `3.DRE 0X.pdf`, `4.Balancete 0X.pdf`), as três competências ficaram completas. Correção do ciclo 1: conta credora dentro das despesas (Vale Transporte 366,93 na DRE 06) reduz despesa em vez de contar como receita. Novo golden `motor_202606_08.json` aprovado pelo usuário (opção a). Não existe trimestre completo sem setembro: 2026-T2 só com junho, 2026-T3 com julho e agosto.
- 2026-09-25 — O usuário renomeou a amostra `2.Resumo da Folha.pdf` para `2.Resumo da Folha 08.pdf` e acrescentou `2.Resumo da Folha 06.pdf` e `2.Resumo da Folha 07.pdf`; testes e `scripts/verify.mjs` atualizados.

---

## 2026-09-25 — Build (SDD Build by RDD) e fechamento do ciclo 2

### O que foi feito

- **Regras versionadas** em `services/worker/rules/2026/`: `manifest.json` (versão `2026.1.0`, hash `e00eaa79e1ae…`, CRLF normalizado), `simples.json` (Anexos I–V transcritos do DOU de 28/10/2016, `verificado: true`), `presumido.json` (LC 224: limite trimestral R$ 1.250.000, fator 1,10, IRPJ desde 01/2026, CSLL desde 04/2026, `verificado: false`), `real.json`, `encargos.json` (CPP 20%, RAT sugerido 2%, FAP 1,0000, terceiros FPAS 515 = 5,8%), `elegibilidade.json`, `atividades.json`.
- **Motor** em `services/worker/src/worker/engine/`: `memory.py`, `rules.py`, `snapshot.py`, `activities.py`, `assumptions.py`, `eligibility.py`, `payroll.py`, `simples.py`, `presumido.py`, `real.py`, `calculate.py`. Simulação idempotente por (snapshot, premissas, regras).
- **Worker** (`db.py`, `pipeline.py`, `export_xlsx.py`): jobs `suggest_assumptions`, `calculate` e `export_simulation`; XLSX em `<office>/<case>/simulations/<sim>.xlsx`. A regeneração de premissas remove as que deixaram de ser sugeridas.
- **Banco** `supabase/migrations/20260925000001_motor.sql`:
  - tabelas `assumptions`, `simulations` e `simulation_lines`, as duas últimas append-only, com RLS;
  - RPCs `request_planning`, `confirm_assumption` (justificativa de ≥ 5 caracteres e validação de tipo via `assumption_value_ok`), `request_calculation` e `request_simulation_export`;
  - a política de Storage bloqueia `/simulations/` para os usuários.
- **Web**: `/cases/[id]/planning` (premissas agrupadas, "Regenerar premissas", "Calcular", lista de simulações, aviso do último cálculo); `/cases/[id]/planning/[simId]` (comparativo, memória, rastreabilidade); `/api/simulations/[id]/export` (redirect 307 para URL assinada); botão "Planejamento" no dossiê homologado.
- **Revisão pós-build aplicada:**
  - Fator R sem folha → "não calculado";
  - tipo do valor validado no banco;
  - chave de atividade com os tributos declarados zero;
  - regeneração de premissas;
  - saldo credor de PIS/Cofins transportado;
  - exclusões também na parte cumulativa;
  - job pendente com motivo visível;
  - página de simulação com falha;
  - regex de conta ICMS/ISS.
- **Evidência final:**
  - `npm run verify` → PASS (pytest 127, pgTAP 63, typecheck, vitest 14);
  - `npx next build` → ok;
  - smoke E2E igual ao golden, escritório B vê 0/0, XLSX de 14.583 bytes, páginas 200, export 307.
- Relatório: `sdd/BUILD_REPORT_MOTOR_TRIBUTARIO.md` (validado).

### Casos e testes em aberto

- Dossiês do escritório A (`a0000000-0000-4000-8000-000000000001`), empresa "Empresa da amostra (smoke)", CNPJ 37.704.456/0001-42, no Supabase local:
  - `6811e832-67d7-4b5b-ad53-cdd8ba2fb708` (06–08/2026, homologado, 3 simulações). O smoke sobrescreveu as declarações de elegibilidade com `nao` (antes estavam "não informado", confirmadas pelo usuário). A simulação `d347ca38-319e-41bd-bfdc-2e7ef59dd370` (Simples indeterminado) foi calculada com as premissas do usuário; `eb2b84ef-d04d-4206-a4a1-0356ffeaba07` é a do golden.
  - `4b37686d-4ab8-4429-ab49-c9c7b312b6a9` (06–08/2026, homologado, 1 simulação). As premissas usam a identificação antiga das atividades e precisam de "Regenerar premissas".
  - `003b9273-0d65-494c-b8ac-c15384ca72a8` (07–08/2026, homologado, 8 arquivos, 1 simulação) e `4eb5545b-9f95-46a0-8bdb-f2420e66ff5b` (07–08/2026, homologado, 30 premissas, 0 simulações). Ambos foram criados pelo usuário na revisão de telas em 2026-09-25, com as folhas novas.
  - `29087d40-7471-490e-85cf-5d8c8f5bb8fd` (06–08/2026, em revisão, 9 arquivos).
- Golden aprovado: 08/2026 é a única competência completa da amostra (PGDAS-D + folha + DRE + balancete). Totais: Simples 23.430,47 · Presumido 26.165,68 (T3 parcial) · Real 63.093,28.
- Login local para as telas: `analista.a@example.com` / `analista.b@example.com`, com a senha do seed local (o usuário digita).

### Pendências

**🐛 Bug fix** — o que ficou quebrado, parcial ou com comportamento errado conhecido:

- Dossiês com premissas geradas antes da correção da chave de atividade (ex.: `4b37686d-4ab8-4429-ab49-c9c7b312b6a9`) calculam o regime como "não calculado — atividade sem perfil confirmado" até alguém clicar em "Regenerar premissas" e reconfirmar as atividades. Afeta só dados locais.
- Nenhum projeto tem lint configurado: não há script `lint` em `apps/web` nem ruff no worker. Risco aceito, registrado no Build Report.

**✨ Feature improvement** — o que é incremento planejado, melhoria ou próxima etapa de escopo:

- Revisão contábil das regras `verificado: false`:
  - LC 224 trimestral (premissa A-002; o achado da revisão foi contestado e fica como risco aceito até a revisão);
  - ICMS/ISS da faixa 6 pela faixa 5;
  - cumulatividade de serviços hospitalares;
  - encargos, elegibilidade e atividades.
  Qualquer mudança = nova versão em `services/worker/rules/2026/` (ex.: `2026.1.1`).
- Amostra com CMV na DRE (a atual não tem, e o lucro do Real sai alto) e amostras de serviços (Anexos III/V com Fator R) para ampliar os goldens.
- Trimestre completo: com PGDAS-D, folha, DRE e balancete de 09/2026 o 2026-T3 fecha; novo golden exigirá nova aprovação.
- Ciclo 3: projeção de 12 meses, sensibilidade, ponto de virada, recomendação/parecer, aprovação do responsável técnico, PDF executivo e custo de conformidade.

### Checklist de fechamento (inventário do que foi conferido)

- **O código roda?** O worker (processo em segundo plano com `WORKER_POLL_SECONDS=1`) e o Next.js em http://localhost:3000 estão em execução, e o smoke E2E percorreu premissas → cálculo → simulação → XLSX.
- **Os critérios de aceite passam?** AT-101 a AT-126 têm evidência no Build Report; `npm run verify` terminou com exit 0 depois das correções.
- **As mudanças estão salvas onde deveriam?** Sim: commitadas na branch `feat/motor-tributario`; ainda não publicadas no remoto.
- **O que quebrou está anotado?** Sim: nas Pendências acima e em "Issues Encountered" do Build Report.

### Próximos passos

1. Conferir as telas de planejamento — http://localhost:3000/cases/6811e832-67d7-4b5b-ad53-cdd8ba2fb708/planning e a simulação `eb2b84ef-d04d-4206-a4a1-0356ffeaba07`. Pronto quando: o usuário confirmar o comparativo e a memória, ou listar ajustes.
2. Regenerar premissas dos dossiês antigos — botão "Regenerar premissas" em `/cases/4b37686d-4ab8-4429-ab49-c9c7b312b6a9/planning`. Pronto quando: as atividades aparecerem pendentes, forem confirmadas e o cálculo gerar simulação com o Simples calculado.
3. Agendar a revisão contábil das regras `verificado: false`. Pronto quando: cada regra tiver o dispositivo legal conferido e `verificado` atualizado numa nova versão de regras, com o golden recalculado e reaprovado se mudar.
4. Iniciar o ciclo 3 com a skill **sdd-brainstorm** (projeção/sensibilidade/recomendação). Pronto quando: existir `sdd/BRAINSTORM_<ciclo 3>.md` aprovado.

### Alertas — o que não quebrar

- O motor lê **somente** o snapshot homologado, as premissas confirmadas e as regras versionadas; simulações e linhas são append-only; a unicidade é (case, snapshot_sha256, assumptions_hash, rules_hash).
- Mudança de regra = nova versão de regras e novo `rules_hash`; nunca editar a versão `2026.1.0` em silêncio. O golden só vale com `approved_by`/`approved_at`, e mudar o valor exige nova aprovação.
- O comparativo **não é recomendação**; o texto das telas diz isso e deve continuar dizendo.
- As amostras reais em `docs/Amostras/` contêm CPF/RG e nunca vão para o Git; o golden não pode ter rótulos com dados pessoais. Os logs levam apenas IDs e códigos.
- `SUPABASE_SERVICE_ROLE_KEY` só no servidor (`apps/web/src/lib/supabase/admin.ts` e no worker). A IA não digita senhas em campos do navegador.
- Rodar o smoke E2E em dossiê próprio, não nos dossiês que o usuário usa para revisar telas.
- **Fora de escopo:** projeção, sensibilidade, ponto de virada, recomendação/parecer, aprovação, PDF executivo, custo de conformidade (ciclo 3); OCR e outros sistemas contábeis além da Alterdata.

### Onde está o trabalho

- Projeto: `C:\Users\User\Documents\BRAVO-BUILDER-PROJETOS\PLANEJAMENTO_TRIB` (monorepo: `apps/web`, `services/worker`, `supabase/`).
- Git: `master` em `https://github.com/diekson-bernardes/planejamento_trib.git` (remoto `origin`, branch padrão); trabalho novo em branch de feature com PR. Apenas `.claude/launch.json` (configuração local do preview) fica fora do Git.
- Artefatos SDD: `sdd/BRAINSTORM_MOTOR_TRIBUTARIO.md`, `sdd/DEFINE_MOTOR_TRIBUTARIO.md`, `sdd/DESIGN_MOTOR_TRIBUTARIO.md`, `sdd/BUILD_REPORT_MOTOR_TRIBUTARIO.md`; ciclo 1 em `sdd/HANDOFF_IMPORTACAO_CONCILIACAO.md`.
- Ambiente local: Docker Desktop + `npx supabase start` (Postgres em `127.0.0.1:54322`, API em `127.0.0.1:54321`), Next.js na porta 3000, worker via `python -m worker.main` com `PYTHONPATH=services\worker\src`.
