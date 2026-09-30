# DEFINE: Atividades mistas e Fator R no Planejamento Rápido

> O dossiê rápido passa a dividir o faturamento entre várias atividades (CNAEs) por percentual e a calcular o Fator R mês a mês com a folha real dos 12 meses anteriores, com tratamento explícito de folha incompleta e simulação informativa da "folha ideal".

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | ATIVIDADES_FATOR_R |
| **Date** | 2026-09-28 |
| **Author** | SDD Define by RDD |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O Planejamento Rápido aplica um único anexo (o do CNAE principal) a todo o faturamento e estima o Fator R pela média da folha × 12 repetida em todos os meses, sem FGTS; para empresas com comércio e serviço, ou com serviço sujeito ao Fator R, o Simples calculado fica distorcido e a recomendação de regime pode se inverter.

---

## Target Users

| User | Role | Pain Point |
|---|---|---|
| Contador/analista do escritório | Monta e homologa o dossiê rápido | Não consegue representar empresa com mais de uma atividade nem ver em que mês o Fator R muda o anexo |
| Administrador/sócio do escritório | Apresenta a recomendação ao cliente | Precisa mostrar quanto de folha falta para chegar ao Anexo III e se isso compensa, via pró-labore ou salário |

---

## Goals

| Priority | Goal |
|---|---|
| **MUST** | Guardar os CNAEs secundários da consulta à Receita (código + descrição) na empresa, sem sócios/QSA |
| **MUST** | Permitir marcar atividades (CNAEs da Receita ou digitados) com percentual do faturamento por atividade, somando exatamente 100,00% |
| **MUST** | Calcular Simples e Presumido por atividade no dossiê rápido, com perfil (anexo, classe do Presumido, Fator R) sugerido pela tabela CNAE e editável |
| **MUST** | Calcular o Fator R por competência = folha dos 12 meses anteriores ÷ RBT12, com folha = salários + pró-labore + FGTS (8% sobre salários) |
| **MUST** | Exigir escolha explícita ("completar pela média" ou "considerar zero") quando houver menos de 12 meses de folha, registrada na premissa e no PDF |
| **MUST** | Manter idênticos os goldens existentes e o resultado de dossiê rápido com uma única atividade |
| **SHOULD** | Mostrar, na tela e no PDF, o quadro do Fator R mês a mês (folha 12m, RBT12, %, anexo) e o quadro de atividades |
| **SHOULD** | Mostrar o bloco informativo "folha ideal" com duas opções lado a lado: via pró-labore (custo INSS 11% do sócio) e via salário (FGTS 8% + provisões de 13º e férias), com a economia de Simples III × V, fora dos totais |
| **COULD** | Incluir manualmente um CNAE não retornado pela Receita |

---

## Success Criteria

- [ ] Goldens `motor_202608`, `motor_202606_08`, `decisao_2026`, `decisao_2027` e `rapido_2027` com diferença de R$ 0,00 em todas as linhas.
- [ ] Dossiê rápido com uma única atividade (100%) produz resultado idêntico, linha a linha, ao da versão atual para o mesmo snapshot — exceto a folha do Fator R, que só existe para atividades com Fator R.
- [ ] Novo golden fictício (sem PII) com comércio (Anexo I) + serviço com Fator R (Anexo III/V), incluindo ao menos uma competência em que o anexo muda, aprovado pelo usuário.
- [ ] 100% das tentativas de homologar com soma ≠ 100,00%, nenhuma atividade marcada ou CNAE inválido são recusadas com mensagem.
- [ ] 100% dos cálculos com atividade de Fator R e folha incompleta sem escolha registrada param com mensagem explícita.
- [ ] `npm run verify` termina com exit 0.

---

## Acceptance Tests

| ID | Pattern | Criterion (EARS) | Gate (`kind`) |
|---|---|---|---|
| AT-601 | Event-driven | **When** a consulta de CNPJ retorna CNAEs secundários, the system **shall** guardar código e descrição de cada um na empresa sem armazenar sócios/QSA | test |
| AT-602 | Event-driven | **When** o analista marca atividades e informa percentuais somando 100,00%, the system **shall** salvar as atividades do dossiê com seus percentuais | test |
| AT-603 | Unwanted | **If** a soma dos percentuais das atividades marcadas for diferente de 100,00%, **then** the system **shall** recusar a homologação com a mensagem da soma atual | test |
| AT-604 | Unwanted | **If** nenhuma atividade estiver marcada ou um CNAE digitado for inválido, **then** the system **shall** recusar a gravação/homologação com mensagem | test |
| AT-605 | Event-driven | **When** só uma atividade é marcada, the system **shall** atribuir 100% a ela automaticamente | test |
| AT-606 | Event-driven | **When** as premissas do dossiê rápido são geradas, the system **shall** criar uma atividade por CNAE marcado com receita = faturamento do mês × percentual e perfil sugerido pela tabela CNAE | test |
| AT-607 | Event-driven | **When** o Simples é calculado para uma atividade com Fator R, the system **shall** usar, em cada competência, a folha (salários + pró-labore + FGTS 8% sobre salários) dos 12 meses anteriores ÷ RBT12 e escolher o Anexo III se ≥ 28% ou o V caso contrário | test |
| AT-608 | Unwanted | **If** houver atividade com Fator R, menos de 12 meses de folha e nenhuma escolha registrada, **then** the system **shall** interromper o cálculo com a mensagem "Fator R: escolha como tratar os meses sem folha" | test |
| AT-609 | Event-driven | **When** a escolha é "completar pela média", the system **shall** preencher os meses sem folha com a média dos meses informados; **when** é "considerar zero", **shall** usar zero nesses meses | test |
| AT-610 | Unwanted | **If** não houver nenhum mês de folha informado, **then** the system **shall** oferecer somente a opção "considerar zero" | test |
| AT-611 | Event-driven | **When** uma atividade com Fator R cai no Anexo V numa competência, the system **shall** gerar linhas informativas "folha ideal" (folha faltante até 28%, custo via pró-labore, custo via salário e economia de Simples III × V) fora dos totais do regime | test |
| AT-612 | Unwanted | **If** um CNAE marcado estiver fora da tabela CNAE, **then** the system **shall** deixar a atividade sem anexo sugerido e impedir o cálculo até o analista escolher o perfil | test |
| AT-613 | Non-regression | The system **shall continue to** produzir os goldens `motor_202608`, `motor_202606_08`, `decisao_2026`, `decisao_2027` e `rapido_2027` sem diferença | test |
| AT-614 | Non-regression | The system **shall continue to** aplicar os percentuais de ICMS-ST e monofásico à empresa inteira, como no ciclo 5 | test |
| AT-615 | State-driven | **While** o dossiê está homologado, the system **shall** impedir a alteração de atividades e percentuais até ser reaberto | test |
| AT-616 | Event-driven | **When** o dossiê rápido é exibido ou emitido em PDF, the system **shall** mostrar o quadro de atividades, o quadro do Fator R mês a mês, a escolha de folha incompleta e o bloco "folha ideal" | test |
| AT-617 | Unwanted | **If** um usuário de outro escritório tentar ler ou alterar atividades de um dossiê, **then** the system **shall** negar pelo RLS | test |

---

## Clarifications

### Session 2026-09-28

- [x] (Data model) O que compõe a folha do Fator R? → salários + pró-labore + FGTS (8% sobre salários), sem CPP (já no DAS do III/V); vale só para o dossiê rápido, sem alterar o dossiê completo; integrado em Goals, AT-607 e Constraints.
- [x] (UX flow) Como a "folha ideal" completa o valor faltante? → mostrar duas opções lado a lado: pró-labore (INSS 11% do sócio) e salário (FGTS 8% + provisões de 13º e férias); integrado em Goals e AT-611.
- [x] (Scope) Soma dos percentuais → exatamente 100,00%, sem tolerância (Brainstorm, checkpoint 1); integrado em AT-603.

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

- Percentual de atividade diferente por mês (sazonalidade).
- Leitura da divisão por atividade a partir do PDF de faturamento ou do PGDAS-D.
- Revisão contábil da tabela CNAE → anexo.
- Otimização automática do pró-labore/folha.
- Atividades mistas e nova composição da folha do Fator R no dossiê completo.
- Percentuais de ICMS-ST/monofásico por atividade.
- IRRF sobre o pró-labore na folha ideal.
- Produção/deploy, mix B2B da Reforma e novas fontes de importação.

---

## Constraints

| Type | Constraint | Impact |
|---|---|---|
| Technical | Reaproveitar o motor multiatividade (`simples.py`, `payroll.py`) e o formato do dossiê completo gerado por `quick_view.py` | Sem motor novo; mudanças concentradas no Rápido |
| Technical | Regimes do Rápido: SIMPLES, SIMPLES_HIBRIDO (2027) e PRESUMIDO | Lucro Real continua fora |
| Technical | RLS por escritório (`is_member`) em tabelas/colunas novas; pgTAP cobrindo acesso cruzado | Migration nova + teste |
| Other | Sem armazenar/logar sócios/QSA; logs só com IDs e códigos | Parser da consulta filtra os campos |
| Other | Chamada real ao n8n só com autorização do usuário; testes usam resposta simulada | Fixtures fictícias |
| Other | Goldens sem PII; `docs/Amostras` fora do git | Golden novo fictício |
| Other | Alíquotas INSS 11%, FGTS 8% e provisões de 13º/férias configuráveis nas regras e marcadas como não verificadas | Linhas da folha ideal mostram "não verificado" |

---

## Technical Context

| Aspect | Value | Notes |
|---|---|---|
| **Deployment Location** | `services/worker/src/worker/engine/quick_view.py`, `simples.py`, `cnpj_lookup.py`, `pipeline.py`; `supabase/migrations/`; `apps/web/src/app/(app)/cases/[id]/`, `components/CompanyCnae.tsx` | Observado no repositório |
| **KB Domains** | Simples Nacional (LC 123/2006 art. 18 §§5-J, 24 — Fator R), Presumido por atividade, encargos da folha | Regras 2026/2027 existentes |
| **IaC Impact** | Modify existing | Migration nova (CNAEs secundários e atividades do dossiê rápido); sem infraestrutura nova |
| **LLM Prompts** | false | Nenhum runtime LLM; a consulta de CNPJ é chamada de ferramenta MCP determinística no n8n |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|---|---|---|---|
| A-001 | A resposta da BrasilAPI via n8n traz `cnaes_secundarios` com código e descrição | Sem sugestão de secundários; usuário digita os CNAEs | no |
| A-002 | Nas competências projetadas (2026 deslocado e 2027), a folha dos 12 meses anteriores usa a folha projetada pela mesma regra de projeção já existente | Fator R projetado divergente; ajustar no Design | no |
| A-003 | O golden `rapido_2027` usa CNAE sem Fator R (4744-0/01, Anexo I), portanto a nova composição da folha não o altera | Golden teria de ser revisto e reaprovado | yes (CNAE da amostra do ciclo 5) |
| A-004 | Presunção do Presumido por atividade segue a classe do perfil já suportada pelo motor | Presumido do misto incorreto | no |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---|---:|---|
| Problem | 3 | Causa observada no código (`quick_view.py:175-210`) e impacto claro |
| Users | 3 | Analista e administrador com dores distintas |
| Goals | 3 | MUST/SHOULD/COULD priorizados |
| Success | 3 | Goldens com R$ 0,00, recusas 100%, verify exit 0 |
| Scope | 2 | Premissas A-001/A-002 dependem de confirmação no Design |
| **Total** | **14/15** | |

Minimum to proceed: **12/15**.

---

## Open Questions

- (não bloqueante) Formato exato do campo de CNAEs secundários na resposta do n8n — confirmar no Design com uma chamada real autorizada ou com a documentação da BrasilAPI.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-28 | SDD Define by RDD | Initial version |

---

## Next Step

Execute o **SDD Design by RDD**.
