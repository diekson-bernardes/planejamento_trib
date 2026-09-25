# DEFINE: Reforma Tributária 2027 (ciclo 4 do Planejamento Tributário)

> Regras de 2027 versionadas (CBS/IBS no lugar de PIS/Cofins, crédito financeiro, IPI zero), projeção de 2027 com quatro alternativas (Simples por dentro, Simples híbrido, Presumido, Real) e importação do Livro de Apuração do ICMS para a base de créditos.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | REFORMA_2027 |
| **Date** | 2026-09-25 |
| **Author** | SDD Define by RDD |
| **Status** | Ready for Design |
| **Clarity Score** | 13/15 |

---

## Problem Statement

O escritório só compara os regimes no exercício de 2026 e não consegue recomendar o regime — nem a opção do Simples por dentro × híbrido — para 2027, ano em que PIS/Cofins são substituídos pela CBS não cumulativa com crédito financeiro sobre as compras; sem isso, a decisão de janeiro de 2027 é tomada fora do sistema, sem memória nem aprovação.

---

## Target Users

| User | Role | Pain Point |
|---|---|---|
| Analista do escritório | Informa alíquotas e crescimento, importa o Livro de Apuração e pede a Projeção 2027 | Precisa comparar as quatro alternativas de 2027 sem planilha paralela |
| Responsável técnico | Revisa e aprova a recomendação de 2027 | Precisa ver as alíquotas-premissa, as regras não conferidas e as ressalvas antes de aprovar |
| Cliente do escritório | Recebe o PDF da recomendação de 2027 | Decide o regime e a opção do Simples para 2027 |

---

## Goals

| Priority | Goal |
|---|---|
| **MUST** | Regras de 2027 como nova versão em `services/worker/rules/2027/`: CBS/IBS com débito sobre a receita e crédito financeiro sobre compras, IPI zero, repartição do DAS de 2027 e demais regras (IRPJ, CSLL, encargos, ICMS/ISS, elegibilidade) vigentes em 2027; regras não conferidas marcadas `verificado: false` |
| **MUST** | Motor calcula por exercício: 2026 inalterado; 2027 com CBS/IBS no lugar de PIS/Cofins no Presumido, no Real e no Simples |
| **MUST** | Quatro alternativas em 2027: Simples por dentro (CBS/IBS no DAS), Simples híbrido (DAS sem CBS/IBS + CBS/IBS no regime regular com créditos), Presumido e Real |
| **MUST** | Alíquotas de CBS e de IBS de 2027 como premissas do escritório por dossiê, sem valor padrão; sem elas confirmadas, a recomendação de 2027 fica bloqueada |
| **MUST** | Projeção 2027 = 12 meses da Projeção 2026 deslocados para 2027 com crescimento da receita (premissa, padrão 0%), passando pela sensibilidade (5 variáveis do ciclo 3 + alíquota da CBS), recomendação, fluxo de aprovação e PDF do ciclo 3 |
| **MUST** | Livro de Apuração do ICMS (Alterdata) importado antes da homologação: parser das entradas e saídas por CFOP com subtotais e totais, validações de soma e conciliação R7 (compras para comercialização 1102, 2102, 1403, 2403 = débitos da conta 13101 do balancete); documento opcional, fora da definição de competência completa |
| **MUST** | Base de créditos de CBS/IBS por mês como premissa: sugerida pelo livro quando presente, senão pela conta 13101; alterável manualmente com justificativa |
| **MUST** | Golden da Projeção 2027 da amostra aprovado pelo usuário no build, após informar as alíquotas |
| **SHOULD** | Saídas do livro comparadas com a receita do PGDAS-D como informação (sem bloquear) |
| **COULD** | Tela mostrando lado a lado a recomendação de 2026 e a de 2027 do mesmo dossiê |

---

## Success Criteria

- [ ] Goldens `motor_202608`, `motor_202606_08` e `decisao_2026` continuam reproduzidos exatamente (100%).
- [ ] O Livro de Apuração de 08/2026 é importado com 100% dos CFOPs de entradas e saídas, validações de soma aprovadas e R7 conciliada com diferença de R$ 0,00 em relação à conta 13101.
- [ ] Projeção 2027 com as quatro alternativas, 100% das linhas com regra (versão 2027) e origem, e mesmo `result_hash` em 100% das reexecuções com as mesmas entradas.
- [ ] Projeção + sensibilidade + recomendação de 2027 concluídas em ≤ 60 s para um dossiê de até 12 competências.
- [ ] 0 recomendações de 2027 não bloqueadas sem alíquota de CBS e de IBS confirmada.
- [ ] Golden de 2027 aprovado pelo usuário com as alíquotas informadas no build.

---

## Acceptance Tests

| ID | Pattern | Criterion (EARS) | Gate (`kind`) |
|---|---|---|---|
| AT-401 | Event-driven | **When** o motor calcula uma competência de 2026, the system **shall** usar as regras de 2026 e produzir o mesmo resultado dos ciclos 2 e 3 | test |
| AT-402 | Event-driven | **When** o motor calcula uma competência de 2027, the system **shall** usar as regras de 2027, sem linhas de PIS, Cofins ou IPI, e com CBS e IBS | test |
| AT-403 | Event-driven | **When** o motor calcula CBS/IBS no Presumido ou no Real em 2027, the system **shall** registrar débito = receita × alíquota e crédito = base de créditos do mês × alíquota, com saldo credor transportado ao mês seguinte | test |
| AT-404 | Event-driven | **When** o motor calcula o Simples por dentro em 2027, the system **shall** incluir CBS/IBS no DAS pela repartição do anexo das regras de 2027 | test |
| AT-405 | Event-driven | **When** o motor calcula o Simples híbrido em 2027, the system **shall** excluir CBS/IBS do DAS e calculá-las pelo regime regular com débito sobre a receita e crédito sobre a base de créditos | test |
| AT-406 | Event-driven | **When** a Projeção 2027 é pedida, the system **shall** deslocar os 12 meses da Projeção 2026 para 2027, aplicar o crescimento confirmado à receita e às grandezas proporcionais e marcar a origem de cada mês | test |
| AT-407 | Unwanted | **If** a alíquota de CBS ou de IBS de 2027 não está confirmada, **then** the system **shall** marcar a recomendação de 2027 como bloqueada, com prévia incompleta | test |
| AT-408 | Event-driven | **When** a recomendação de 2027 é calculada, the system **shall** ordenar as quatro alternativas elegíveis, aplicar o limiar do escritório e explicar a escolha com fatores e economia vs. o regime atual e o segundo colocado | test |
| AT-409 | Event-driven | **When** a sensibilidade de 2027 roda, the system **shall** incluir a alíquota da CBS entre as variáveis, com ponto de virada ou "sem virada no intervalo" | test |
| AT-410 | Event-driven | **When** o Livro de Apuração do ICMS de 08/2026 é enviado, the system **shall** classificá-lo como Livro de Apuração, extrair entradas e saídas por CFOP com página de origem e aprovar as validações de soma | test |
| AT-411 | Unwanted | **If** a soma das entradas por CFOP não bate com os subtotais ou totais do livro, **then** the system **shall** marcar a validação como falha e exibir a diferença | test |
| AT-412 | Event-driven | **When** o dossiê tem Livro de Apuração e balancete da mesma competência, the system **shall** conciliar R7 (compras para comercialização × débitos da conta 13101) pela tolerância do escritório | test |
| AT-413 | Unwanted | **If** R7 diverge acima da tolerância sem justificativa, **then** the system **shall** bloquear a homologação, como nas regras R1–R6 | test |
| AT-414 | Where | **Where** o livro está presente, the system **shall** sugerir a base de créditos do mês pelas entradas creditáveis do livro; **where** não está, pela conta 13101 do balancete | test |
| AT-415 | Unwanted | **If** o usuário tenta anexar documento a dossiê homologado, **then** the system **shall** recusar e manter a premissa manual como forma de informar a base de créditos | test |
| AT-416 | Unwanted | **If** o Livro de Apuração tem CNPJ diferente do dossiê, **then** the system **shall** marcar o arquivo como CNPJ divergente | test |
| AT-417 | Event-driven | **When** a Projeção 2027 de um dossiê de até 12 competências é pedida, the system **shall** concluir projeção, sensibilidade e recomendação em até 60 s | test |
| AT-418 | Event-driven | **When** uma recomendação de 2027 aprovada é emitida, the system **shall** gerar o PDF com o título do exercício 2027, as quatro alternativas, as alíquotas-premissa e a ressalva de regras não conferidas | test |
| AT-419 | Event-driven | **When** o motor projeta 2027 com as amostras e as alíquotas informadas pelo usuário, the system **shall** reproduzir exatamente o golden aprovado | test |
| AT-420 | Non-regression | The system **shall continue to** reproduzir exatamente os goldens `motor_202608`, `motor_202606_08` e `decisao_2026` | test |

---

## Clarifications

### Session 2026-09-25

- [x] (NFRs) Tempo máximo da Projeção 2027 (projeção + sensibilidade + recomendação, até 12 competências)? → até 60 s; integrado em Success Criteria e AT-417
- [x] (Edge cases / Data model) Quando o Livro de Apuração pode entrar? → antes da homologação, dentro do snapshot; em dossiê homologado, só a premissa manual (sugestão pela conta 13101); integrado em Goals, AT-414 e AT-415
- Varredura das 9 categorias: Scope (Clear: YAGNI do Brainstorm), Data model (Clear após clarificação: novo tipo de documento, R7, premissas de alíquota, crescimento e base de créditos, projeções por exercício), UX flow (Clear: premissas → Projeção 2027 → recomendação → aprovação → PDF), NFRs (Clear após clarificação), Integrations (Clear: pipeline de importação, motor e fluxo existentes), Edge cases (Clear: AT-407, AT-411, AT-413, AT-415, AT-416), Constraints (Clear), Terminology (Clear: "por dentro" = CBS/IBS no DAS; "híbrido" = CBS/IBS fora do DAS pelo regime regular; "base de créditos" = compras creditáveis do mês; "Livro de Apuração" = Registro de Apuração do ICMS Alterdata), Done signal (Clear: golden 2027 aprovado no build).

---

## Verify Gate

```yaml
verify_gate:
  kind: test
  cmd: "npm run verify"
  pass_when: "exit 0"
  threshold: "—"
  manual_fallback: "—"
```

---

## Out of Scope

- Mix de vendas e efeito no crédito do cliente B2B (próximo ciclo).
- Transição 2029–2033 (ICMS/ISS reduzidos e IBS crescente), Imposto Seletivo, exceção da Zona Franca de Manaus no IPI, alíquotas reduzidas por produto/NCM, split payment e opção semestral do híbrido (próximo ciclo).
- Anexar documentos a dossiê já homologado ou reabrir homologação.
- Novos layouts/sistemas (OCR, XLSX, Domínio, Questor, Netsped) e decisão mais rica (sazonalidade, cenários, RF-14/RF-15, assinatura eletrônica).

---

## Constraints

| Type | Constraint | Impact |
|---|---|---|
| Technical | Regras por exercício: `rules/2026` intocadas (versão 2026.1.0); 2027 em nova versão | Goldens dos ciclos 2 e 3 são regressão obrigatória |
| Technical | Alíquotas de CBS/IBS sem valor padrão nas regras (premissa do escritório) | Sem premissa confirmada, 2027 fica bloqueado |
| Technical | Livro de Apuração opcional, fora da definição de competência completa | Não altera snapshots nem goldens existentes |
| Technical | Verify Gate `npm run verify` ampliado com os testes do ciclo 4 | Build precisa incluir pytest, pgTAP e testes web novos |
| Resource | Uma única amostra do Livro de Apuração (08/2026) | Parser com um layout Alterdata; meses sem livro usam a conta 13101 |
| Resource | LC 214/2025 não conferida na fonte primária; KB sem a repartição do DAS de 2027 | Regras 2027 com `verificado: false` e pesquisa complementar na KB durante o Design |
| Other | Janela de opção pelo híbrido para o 1º semestre de 2027 (30/09/2026, segundo as fontes) não é atendida por este ciclo | Decisão dessa janela fica fora do sistema |
| Timeline | N/A (não informado) | — |

---

## Technical Context

| Aspect | Value | Notes |
|---|---|---|
| **Deployment Location** | `services/worker/rules/2027/`, `services/worker/src/worker/engine/` (cálculo por exercício, projeção 2027, sensibilidade, recomendação), `services/worker/src/worker/parsers/` e `classify.py` (Livro de Apuração), `services/worker/src/worker/reconcile.py` (R7), `supabase/migrations/`, `apps/web/src/app/(app)/cases/[id]/planning/` | Mesmo monorepo e padrões dos ciclos 1–3 |
| **KB Domains** | `reforma-tributaria`, `simples-nacional`, `lucro-presumido`, `lucro-real`, `documentos-fonte`, `planejamento-comparativo` | Calendário, Simples na Reforma, opção pelo regime regular, layouts Alterdata |
| **IaC Impact** | None | Sem recurso novo; imagem do worker já copia `rules/` |
| **LLM Prompts** | false | Nenhum provedor/modelo de LLM, prompt ou RAG no Brainstorm; cálculo e textos determinísticos |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|---|---|---|---|
| A-401 | No Simples por dentro de 2027 a alíquota efetiva do anexo é a mesma de 2026 e a parcela de PIS/Cofins da repartição passa a ser de CBS/IBS | Total do Simples por dentro em 2027 muda | no |
| A-402 | No Simples híbrido, o DAS exclui a parcela de CBS/IBS da repartição e a empresa paga CBS/IBS = receita × alíquota − base de créditos × alíquota | Custo do híbrido muda | no |
| A-403 | Em 2027, IRPJ, CSLL, encargos da folha, ICMS/ISS e regras de elegibilidade seguem as de 2026 | Presumido, Real e Simples de 2027 mudam | no |
| A-404 | Base de créditos creditável = compras para comercialização + fretes (CFOP 1102, 2102, 1403, 2403, 2353 e equivalentes); devoluções de venda (1202, 1411) reduzem o débito | Crédito de CBS/IBS muda | no |
| A-405 | O crescimento de 2027 multiplica a receita e as grandezas proporcionais (compras, ICMS, lucro), mantendo margem e folha/receita | Projeção 2027 muda | yes (Brainstorm, Q4) |
| A-406 | ICMS/ISS não integram a base de CBS/IBS em 2027 | Débito de CBS/IBS muda | no |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---|---:|---|
| Problem | 3 | Dor, usuários e impacto explícitos |
| Users | 3 | Analista, responsável técnico e cliente |
| Goals | 3 | MUST/SHOULD/COULD alinhados ao Brainstorm e ao YAGNI |
| Success | 2 | Critérios numéricos; golden de 2027 depende das alíquotas informadas no build |
| Scope | 2 | Fronteiras claras; repartição do DAS de 2027 e tratamento de ICMS/ISS na base (A-401, A-406) dependem de pesquisa no Design |
| **Total** | **13/15** | |

Minimum to proceed: **12/15**.

---

## Open Questions

- Não bloqueante: repartição do DAS de 2027 por anexo e faixa (A-401) e composição da base de CBS/IBS (A-406) — pesquisar na LC 214/2025 durante o Design e registrar nas regras 2027 com fonte e `verificado: false`.
- Não bloqueante: intervalo de variação da alíquota da CBS na sensibilidade — definir no Design a partir da faixa usada pelas fontes.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-25 | SDD Define by RDD | Initial version |

---

## Next Step

Execute o **SDD Design by RDD**.
