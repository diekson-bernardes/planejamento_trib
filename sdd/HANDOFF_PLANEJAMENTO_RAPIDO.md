# HANDOFF: Planejamento Rápido (ciclo 5)

> Registro do que ficou pronto e do que vem depois. Um arquivo por feature — cada etapa nova entra como seção no topo, nunca como arquivo separado.

## Ficha da feature

| Campo | Valor |
|---|---|
| **Objetivo** | Comparar, para 2027, o Simples Nacional por dentro, o Simples por fora (híbrido) e o Lucro Presumido de uma empresa a partir só do faturamento dos últimos 12 meses, da folha e da DRE (PDF ou digitados), com CNAE consultado na Receita e o mesmo fluxo de homologação, aprovação do responsável técnico e PDF do dossiê completo. |
| **Status** | 🔨 em andamento (build completo e commitado; falta push, PR e merge) |
| **Feito** | Brainstorm, Define e Design (2026-09-26, commit `ab8778c`); Build com Verify Gate verde, revisão pós-build aplicada e golden `rapido_2027` aprovado (2026-09-28, commit `9f051b3`) |
| **Falta** | Commit deste handoff, push da branch `feat/planejamento-faturamento-12m`, PR para `master` e merge pelo usuário; revisão contábil da tabela CNAE → anexo e das regras de 2027 antes do uso com clientes |
| **Pronto quando** | O PR do ciclo 5 estiver merged na `master` com `npm run verify` = "VERIFY GATE: PASS" na branch (pytest 218, pgTAP 128, typecheck, vitest 22) |

---

## Eventos

- 2026-09-26 — Escopo definido pelo usuário: rotina nova de "planejamento rápido" (faturamento 12 meses + folha + DRE, PDF ou digitação), só 2027, sem Lucro Real; CNAE pela automação n8n do usuário com fallback digitado; tabela CNAE → anexo cobrindo todos os anexos.
- 2026-09-28 — Durante o Build, a base de créditos de CBS/IBS do rápido passou a não ter sugestão (sem livro/balancete, a sugestão zero dava crédito falso); golden apresentado já com créditos informados e aprovado pelo usuário.

---

## 2026-09-28 — Build do ciclo 5

### O que foi feito

- **Banco:** `supabase/migrations/20260926000005_planejamento_rapido.sql` (aplicada no banco local) — `tax_cases.kind` (`completo`/`rapido`), doc_type `DECLARACAO_FATURAMENTO`, colunas `companies.cnae_*`, tabela `manual_values` (RLS, escrita só por RPC, imutável após homologação), RPCs `enter_manual_values`, `clear_manual_values`, `request_company_lookup` (uma consulta por vez), `set_company_cnae`, `rapido_blockers` (com checagem de escritório); `homologate_case`, `request_calculation` e `request_projection` por tipo (rápido: só 2027). pgTAP em `supabase/tests/planejamento_rapido.test.sql` (20 asserts).
- **Worker:** parser `parsers/declaracao_faturamento.py` (layout da amostra `RBT12.pdf`); validações soma = Total Geral e 12 meses consecutivos; `engine/cnae.py` + `rules/cnae_anexos.json` (82 prefixos, versão 2026.1.0, `verificado: false`); `engine/quick_view.py` (snapshot rápido → formato do dossiê completo, atividades normal/ST/monofásico, sugestões do rápido); linha informativa `faixa` no Simples; parâmetro de regimes em `calculate`/`project`/sensibilidade; `cnpj_lookup.py` (cliente MCP) e job `lookup_company`; PDF com "planejamento rápido", CNAE, faixa e origem PDF × digitado.
- **Web:** tipo do dossiê na criação; seção de CNAE (consultar/digitar) e de digitação mês a mês na página do dossiê; planejamento do rápido só com "Projetar 2027"; tabela "Faixa do Simples Nacional por mês" na projeção.
- **Golden:** `services/worker/tests/golden/rapido_2027.json` — aprovado por Diekson Bernardes em 2026-09-28: Simples 445.983,00 < híbrido 532.676,31 < Presumido 536.469,60; recomendado Simples (19,44% abaixo do híbrido); 5ª faixa jan–jul e 6ª ago–dez de 2027.
- **Revisão pós-build:** 6 achados corrigidos com teste (vazamento em `rapido_blockers` entre escritórios; grupo `rapido` fora da tela; créditos sugeridos como zero; parâmetro sombreado em `calculate`; perfil sem `choices`; consultas de CNAE repetidas).
- **Documentos:** `sdd/BUILD_REPORT_PLANEJAMENTO_RAPIDO.md`; README (seção do ciclo 5 e `CNPJ_LOOKUP_MCP_URL`); KB `kb/simples-nacional/concepts/cnae-e-anexo.md`.

### Casos e testes em aberto

- **Automação de CNAE:** servidor MCP do n8n em `https://webhook.dieksonbernardes.com.br/mcp/consulta-cnpj`, ferramenta `Consultar_CNPJ` (entrada: o CNPJ com 14 dígitos, no campo `cnpj`), resposta = texto JSON com lista de 1 objeto da BrasilAPI; **sem autenticação**. Uma chamada real feita no build com o CNPJ 37704456000142 (CNAE 4744001 + 7 secundários), sem gravar sócios. Em 2026-09-28, com autorização do usuário, uma consulta real pelo caminho completo do app (RPC `request_company_lookup` → job `lookup_company` → worker com `CNPJ_LOOKUP_MCP_URL` → automação) concluiu em 8,3 s na 1ª tentativa: empresa 803b7c97 gravada com CNAE 4744001, origem "receita", 7 secundários só com código e descrição; tela do dossiê mostra CNAE e "consulta à Receita"; log do worker sem dados pessoais.
- **Smoke do ciclo 5** no dossiê local `ad17fd06-ae22-4daa-ab6e-6c6eebb0d1ff` (escritório seed `a0000000-0000-4000-8000-000000000001`): projeção `cd5a226c-3303-4c5e-849b-b4b3115b8c13`, recomendação `3ca48ecf-194b-440e-b474-df6a0f16fde8` emitida (PDF 18.549 bytes). A empresa do seed (CNPJ 37704456000142) ficou com CNAE 4744001 digitado.
- **Amostra nova:** `docs/Amostras/RBT12.pdf` (Declaração de Faturamento 09/2025–08/2026, Total Geral R$ 3.719.883,51; contém CPF e CRC — fora do Git).

### Checklist de fechamento (inventário)

- **O código roda?** `npm run verify` terminou com "VERIFY GATE: PASS" (pytest 218, pgTAP Files=6 Tests=128, typecheck, vitest 22); `next build` e `docker build` + `docker run` concluídos; smoke E2E completo.
- **Os critérios de aceite passam?** AT-501 a AT-519 com evidência no `BUILD_REPORT_PLANEJAMENTO_RAPIDO.md`; AT-514 com ressalva de redação (Simples sai como "não calculado" + alerta de teto, não "inelegível").
- **As mudanças estão salvas onde deveriam?** Código e documentos do SDD commitados na branch (`ab8778c`, `9f051b3`); este handoff ainda não commitado; branch sem push.
- **O que quebrou está anotado?** Sim — nada quebrado conhecido; desvios no Build Report e em Pendências.

### Pendências

**🐛 Bug fix** — o que ficou quebrado, parcial ou com comportamento errado conhecido:

- nenhuma

**✨ Feature improvement** — o que é incremento planejado, melhoria ou próxima etapa de escopo:

- Commit deste handoff, push e PR do ciclo 5.
- Proteger a automação n8n com token (hoje qualquer pessoa com a URL consulta e consome a cota da BrasilAPI) e passar o token por variável de ambiente do worker.
- Revisão contábil da tabela `services/worker/rules/cnae_anexos.json` (LC 123/2006 e Resolução CGSN 140/2018, texto oficial não conferido) e das regras de 2027 (hipótese A-401).
- Distribuir a receita entre CNAE principal e secundários (SHOULD do Define, adiado; hoje 100% no principal).
- Receita bruta da DRE digitada é só informativa: comparar com o faturamento da declaração.
- ICMS no regime normal do rápido é sugerido pelo proxy do DAS; com ST = 0% o ICMS fica alto — orientar o analista a informar a parcela com ST.
- Soma de % ST + % monofásico > 100% só é recusada ao projetar (não na confirmação da premissa).

### Próximos passos

1. Commitar este handoff — `git add sdd/HANDOFF_PLANEJAMENTO_RAPIDO.md` e commit terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Pronto quando: `git status` limpo (exceto `.claude/`).
2. Push e PR para `master` em `https://github.com/diekson-bernardes/planejamento_trib` a partir de `feat/planejamento-faturamento-12m`, corpo terminando com "🤖 Generated with [Claude Code](https://claude.com/claude-code)". Pronto quando: PR aberto (o `gh` não está instalado nesta máquina — abrir pelo Chrome logado do usuário).
3. Merge feito pelo usuário. Pronto quando: PR merged na `master`.
4. Proteger a automação n8n com token e configurar `CNPJ_LOOKUP_MCP_URL` no ambiente do worker. Pronto quando: chamada sem token recusada e job `lookup_company` grava o CNAE com o token.
5. Revisão contábil da tabela CNAE → anexo. Pronto quando: cada entrada conferida ou corrigida numa nova versão com `verificado` atualizado.

### Alertas — o que não quebrar

- Goldens exatos: `motor_202608`, `motor_202606_08`, `decisao_2026`, `decisao_2027` e `rapido_2027`; mudança de número exige nova aprovação do usuário.
- O dossiê rápido entra no motor só por `engine/quick_view.py`; não alterar o motor para ele. A linha `faixa` é informativa (fora dos totais).
- `rules/cnae_anexos.json` tem versão/hash próprios; não colocar dentro de `rules/2026` ou `rules/2027` (mudaria o hash das regras e os goldens).
- Consulta de CNPJ: nunca gravar nem logar sócios (QSA) nem dados pessoais da resposta; chamar a automação real só com autorização do usuário.
- Parar o worker em segundo plano antes de `npm run verify`. Worker local: `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` de `npx supabase status -o env` (+ `CNPJ_LOOKUP_MCP_URL` para consultar CNAE).
- Segurança: não digitar senhas no navegador; `docs/Amostras` (CPF/RG/CRC) fora do Git; goldens sem dados pessoais; `.env*` fora do Git; smoke só em dossiê próprio; merge é do usuário.
- **Fora de escopo:** Lucro Real no rápido, comparativo de 2026 no rápido, outros layouts de faturamento/folha/DRE, XLSX, mix B2B, transição 2029–2033, IS, ZFM, NCM, split payment, conciliação R1–R7 no rápido.

### Onde está o trabalho

Projeto `C:\Users\User\Documents\BRAVO-BUILDER-PROJETOS\PLANEJAMENTO_TRIB`, branch `feat/planejamento-faturamento-12m` (a partir da `master` em `8960b4c`), commits `ab8778c` e `9f051b3`, sem push; remoto `origin` = `https://github.com/diekson-bernardes/planejamento_trib.git`. Documentos em `sdd/*_PLANEJAMENTO_RAPIDO.md`. Supabase local com a migration `20260926000005_planejamento_rapido.sql` aplicada.

---

## 2026-09-26 — Brainstorm, Define e Design

Brainstorm (abordagem A: dossiê simplificado com snapshot montado), Define (Clarity 14/15, 19 ATs, Verify Gate `npm run verify`) e Design (26 itens de manifest, 8 decisões) gravados em `sdd/BRAINSTORM_PLANEJAMENTO_RAPIDO.md`, `sdd/DEFINE_PLANEJAMENTO_RAPIDO.md` e `sdd/DESIGN_PLANEJAMENTO_RAPIDO.md`; commit `ab8778c`.
