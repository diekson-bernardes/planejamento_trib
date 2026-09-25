# DEFINE: Motor Tributário — Elegibilidade e Cálculo dos Regimes (ciclo 2)

> A partir de um dossiê homologado, o sistema sugere premissas, o analista as confirma, e um motor determinístico calcula elegibilidade e custo de Simples Nacional, Lucro Presumido e Lucro Real nas competências completas, com memória de cálculo auditável e comparativo ordenado — sem recomendação.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | MOTOR_TRIBUTARIO |
| **Date** | 2026-09-24 |
| **Author** | SDD Define by RDD (responsável de negócio: Diekson Porto Bernardes) |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Depois de homologar os dados de um cliente, o analista do escritório ainda calcula à mão (ou em simulador externo, como o Econet) quanto a empresa pagaria no Simples, no Presumido e no Real, sem trilha até os documentos, sem controle das premissas e sem versão das regras aplicadas — o que torna o comparativo lento, difícil de revisar e impossível de reproduzir.

---

## Target Users

| User | Role | Pain Point |
|---|---|---|
| Analista contábil/fiscal | Membro do escritório que confirma premissas e dispara o cálculo | Refazer em planilha/simulador os três regimes e explicar a origem de cada número |
| Responsável técnico / contador | Revisa premissas, regras e resultados antes de virar parecer (ciclo 3) | Não consegue auditar como o simulador externo chegou ao valor |
| Administrador do escritório | Garante uso de regras versionadas e rastreáveis | Regras mudam (LC 224/2025) e não há registro de qual versão foi usada |

---

## Goals

| Priority | Goal |
|---|---|
| **MUST** | Calcular somente a partir do snapshot homologado (conteúdo + SHA-256) e de premissas confirmadas; nunca das tabelas vivas |
| **MUST** | Identificar as competências completas (PGDAS-D + folha + DRE + balancete) e marcar as demais como "fora do cálculo" |
| **MUST** | Sugerir automaticamente as premissas ausentes nos documentos, com origem, e permitir confirmar ou alterar com justificativa, autor e data |
| **MUST** | Bloquear o cálculo enquanto houver premissa pendente |
| **MUST** | Avaliar elegibilidade dos três regimes: elegível, elegível com alerta, inelegível (motivo + regra) ou indeterminado (declaração ausente) |
| **MUST** | Calcular o Simples mês a mês: RBT12, anexo por atividade, Fator R, faixa, alíquota efetiva, repartição, exclusões por ST/monofásico, ICMS/ISS pela faixa 5 quando a faixa 6 ainda recolhe no DAS, CPP fora do DAS no Anexo IV |
| **MUST** | Calcular o Presumido por trimestre: presunção por atividade, receitas somadas integralmente, IRPJ 15% + adicional, CSLL 9%, LC 224/2025, PIS/Cofins cumulativo mensal |
| **MUST** | Calcular o Real por trimestre: lucro da DRE + adições − exclusões, compensação limitada a 30%, IRPJ + adicional, CSLL, PIS/Cofins não cumulativo com créditos por premissa e receitas mantidas no cumulativo (ex.: serviços hospitalares) |
| **MUST** | Somar encargos de folha por regime (CPP 20%, RAT × FAP, terceiros por FPAS) e ICMS/ISS por premissa |
| **MUST** | Regras em arquivos versionados com vigência e fonte legal; cada simulação grava versão e hash das regras |
| **MUST** | Gravar simulação com memória por linha (regime, competência, tributo, base, alíquota, valor, regra, origem) e isolamento por escritório (RLS) |
| **MUST** | Exibir comparativo mensal e total por tributo, ordenado por custo total entre os elegíveis, com drill-down até a regra e a origem |
| **MUST** | Regra ausente para a competência/atividade → regime "não calculado" com pendência técnica, nunca estimativa silenciosa |
| **SHOULD** | Nova simulação a cada mudança de premissa ou de versão de regra, preservando as anteriores |
| **SHOULD** | Exportar a memória de cálculo da simulação em XLSX |
| **COULD** | Exibir lado a lado duas simulações do mesmo dossiê |

---

## Success Criteria

- [ ] O DAS recalculado pelo motor para 06, 07 e 08/2026 da amostra (CNPJ 37.704.456/0001-42) é igual ao declarado no PGDAS-D em cada tributo (IRPJ, CSLL, Cofins, PIS, CPP, ICMS, IPI, ISS) e no total, com diferença ≤ R$ 0,01.
- [ ] O caso dourado da KB para o Presumido (comércio, receita trimestral R$ 900.000,00) resulta em IRPJ 10.800,00; adicional 1.200,00; CSLL 9.720,00; PIS 5.850,00; Cofins 27.000,00; total R$ 54.570,00.
- [ ] O caso dourado da KB para o Real (lucro contábil 200.000,00; adições 20.000,00; exclusões 10.000,00; prejuízo acumulado 150.000,00) resulta em compensação 63.000,00; IRPJ 22.050,00; adicional 8.700,00; CSLL 13.230,00; total R$ 43.980,00; saldo de prejuízo R$ 87.000,00.
- [ ] Os valores de Presumido e Real da amostra de 08/2026 conferem com o golden aprovado pelo usuário (valor congelado no Build somente após aprovação registrada).
- [ ] 100% das linhas de simulação têm base, alíquota/fórmula, regra com versão e origem (valor do snapshot ou premissa).
- [ ] Reexecutar o cálculo com o mesmo snapshot, as mesmas premissas e a mesma versão de regras produz o mesmo hash de resultado.
- [ ] 0 regimes inelegíveis ou indeterminados no ordenamento; 100% deles exibem motivo.
- [ ] 0 cálculos executados com premissa pendente.
- [ ] Uma simulação de até 12 competências fica pronta em ≤ 60 s após a confirmação das premissas.
- [ ] 0 acessos entre escritórios às premissas e simulações (testes de RLS).
- [ ] `npm run verify` termina com exit 0.

---

## Acceptance Tests

| ID | Pattern | Criterion (EARS) | Gate (`kind`) |
|---|---|---|---|
| AT-101 | Event-driven | **When** o analista abre o planejamento de um dossiê homologado, the system **shall** listar as competências completas e marcar como "fora do cálculo" as que não têm os quatro documentos | test |
| AT-102 | Unwanted | **If** o dossiê não está homologado, **then** the system **shall** recusar o planejamento com a mensagem "Planejamento exige dossiê homologado" | test |
| AT-103 | Event-driven | **When** o planejamento é iniciado, the system **shall** gerar premissas sugeridas (atividade/presunção por receita, ICMS/ISS, créditos de PIS/Cofins, adições, exclusões, saldo de prejuízo, RAT/FAP, terceiros, declarações de elegibilidade), cada uma com a origem | test |
| AT-104 | Event-driven | **When** o analista altera o valor sugerido de uma premissa, the system **shall** exigir justificativa com ao menos 5 caracteres e registrar autor, data, valor sugerido e valor confirmado | test |
| AT-105 | Unwanted | **If** existe premissa pendente de confirmação, **then** the system **shall** bloquear o cálculo e listar as premissas pendentes | test |
| AT-106 | Event-driven | **When** o cálculo roda, the system **shall** gravar a simulação com hash do snapshot, hash das premissas, versão e hash das regras | test |
| AT-107 | Event-driven | **When** o motor calcula o Simples de 06, 07 e 08/2026 da amostra, the system **shall** obter por tributo os mesmos valores do DAS declarado no PGDAS-D, com diferença ≤ R$ 0,01 | test |
| AT-108 | State-driven | **While** o RBT12 está na faixa 6 e o sublimite ainda não produz efeito, the system **shall** calcular ICMS/ISS com a alíquota efetiva e a repartição da faixa 5 | test |
| AT-109 | Event-driven | **When** a receita de uma atividade tem ICMS-ST ou PIS/Cofins monofásico, the system **shall** zerar a parcela do tributo correspondente na repartição do Simples | test |
| AT-110 | Event-driven | **When** uma atividade sujeita ao Fator R é calculada, the system **shall** usar folha e receita dos 12 meses anteriores ao período e escolher Anexo III se r ≥ 28% e Anexo V se r < 28%, registrando r na memória | test |
| AT-111 | Event-driven | **When** o motor calcula o Presumido do caso dourado de comércio (receita trimestral R$ 900.000,00), the system **shall** obter total federal de R$ 54.570,00 com os valores por tributo do golden | test |
| AT-112 | Where | **Where** a receita bruta acumulada no ano passa de R$ 5.000.000,00, the system **shall** multiplicar por 1,10 a presunção da parcela excedente, para IRPJ desde 01/2026 e para CSLL desde 04/2026 | test |
| AT-113 | Event-driven | **When** o motor calcula o Real do caso dourado da KB, the system **shall** limitar a compensação a 30% do lucro ajustado e obter total de R$ 43.980,00 e saldo de prejuízo de R$ 87.000,00 | test |
| AT-114 | Where | **Where** a premissa indica receita mantida no regime cumulativo (ex.: serviços hospitalares), the system **shall** aplicar PIS 0,65% e Cofins 3% a essa receita também no Real | test |
| AT-115 | Event-driven | **When** o trimestre do Presumido ou do Real não tem as três competências completas, the system **shall** calcular com os meses disponíveis e marcar o trimestre como "parcial" | test |
| AT-116 | Unwanted | **If** a receita do ano projetada pelos dados ou a declaração de elegibilidade indicar impedimento, **then** the system **shall** marcar o regime como inelegível com motivo e regra e excluí-lo do ordenamento | test |
| AT-117 | Unwanted | **If** falta a declaração de elegibilidade necessária (sócio PJ, participações, débitos, atividade vedada), **then** the system **shall** marcar o regime como indeterminado e o comparativo como incompleto | test |
| AT-118 | Unwanted | **If** não existe regra vigente para a competência ou atividade, **then** the system **shall** marcar o regime como "não calculado" com pendência técnica, sem estimar valor | test |
| AT-119 | Event-driven | **When** o motor soma os encargos de folha, the system **shall** aplicar CPP 20% + RAT × FAP + terceiros no Presumido, no Real e no Anexo IV, e nenhum encargo patronal fora do DAS nos Anexos I, II, III e V | test |
| AT-120 | Ubiquitous | The system **shall** gravar em cada linha da simulação a base, a alíquota ou fórmula, o valor, a regra com versão e a origem (valor do snapshot ou premissa) | test |
| AT-121 | Event-driven | **When** o cálculo é reexecutado com o mesmo snapshot, as mesmas premissas e a mesma versão de regras, the system **shall** produzir o mesmo hash de resultado sem duplicar a simulação | test |
| AT-122 | Event-driven | **When** uma premissa ou a versão das regras muda, the system **shall** gerar uma nova simulação e preservar as anteriores | test |
| AT-123 | Event-driven | **When** a simulação termina, the system **shall** exibir o comparativo mensal e total por tributo, ordenado por custo total apenas entre os regimes elegíveis | test |
| AT-124 | Unwanted | **If** um usuário tenta ler premissas ou simulações de outro escritório, **then** the system **shall** negar via RLS, retornando zero linhas | test |
| AT-125 | Event-driven | **When** as premissas de um dossiê de até 12 competências são confirmadas, the system **shall** concluir a simulação em ≤ 60 s | smoke |
| AT-126 | Event-driven | **When** o motor calcula Presumido e Real da amostra de 08/2026, the system **shall** reproduzir exatamente o golden aprovado pelo usuário | test |

---

## Clarifications

### Session 2026-09-24

- [x] (NFRs) Tempo máximo do cálculo → ≤ 60 s por dossiê de até 12 competências; integrado em Success Criteria e AT-125
- [x] (Done signal) Golden de Presumido e Real com a amostra de 08/2026 → o motor calcula no Build, o usuário confere e aprova a memória, e só então o valor é congelado; sem aprovação, o item fica bloqueado; integrado em Success Criteria, AT-126 e Assumptions
- [x] (Scope / Constraints) Vigência das regras → somente exercício 2026 (inclui LC 224: IRPJ desde 01/2026, CSLL desde 04/2026); competência de outro ano → "não calculado"; integrado em Goals, AT-112, AT-118 e Constraints
- [x] (Done signal) Verify Gate → `npm run verify` ampliado com pytest do motor, pgTAP das novas tabelas e typecheck/vitest do web; integrado em Verify Gate
- Varredura das 9 categorias: Scope (Clear), Data model (Clear: premissas, simulações e linhas de memória com RLS), UX flow (Clear: planejamento → premissas → cálculo → comparativo), NFRs (Clear após clarificação), Integrations (Clear: somente snapshot e fila do ciclo 1), Edge cases (Clear: AT-102, AT-105, AT-115 a AT-118), Constraints (Clear), Terminology (Clear: "competência completa" = mês com PGDAS-D, folha, DRE e balancete homologados; "premissa" = valor não extraído, confirmado pelo analista; "simulação" = execução imutável do motor), Done signal (Clear após clarificação).

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

- Projeção de 12 meses, sensibilidade, ponto de virada, recomendação/parecer, fluxo de aprovação do responsável técnico, PDF executivo e custo de conformidade (ciclo 3).
- Lucro Real anual por estimativa com balancete de suspensão.
- Remuneração de sócios (pró-labore × dividendos, Lei 15.270/2025) e JCP.
- CBS/IBS e demais efeitos da reforma tributária.
- Regras para exercícios diferentes de 2026.
- Tela de administração/publicação de regras.
- ICMS por NCM, DIFAL, MEI.
- Uso do PDF Econet (CONESP) como caso dourado.

---

## Constraints

| Type | Constraint | Impact |
|---|---|---|
| Technical | Entrada exclusiva: snapshot homologado do ciclo 1 + premissas confirmadas | O motor não lê `extracted_values` nem outras tabelas vivas |
| Technical | Stack do ciclo 1: worker Python (fila `jobs`, `Decimal`), Supabase com RLS por escritório, Next.js | Novo job no worker; novas tabelas com RLS; novas telas no site |
| Technical | Regras em arquivos versionados com vigência e fonte legal; simulação grava versão e hash | Mudança de regra exige nova versão e deploy |
| Technical | Regra ausente nunca é estimada | Regime "não calculado" com pendência |
| Technical | Verify Gate `npm run verify` ampliado | Build precisa acrescentar os testes do motor ao gate existente |
| Resource | Amostras de um único cliente comercial (Anexo I), com 08/2026 como única competência completa | Serviços (Anexos III/V, Fator R) e Real com prejuízo dependem de casos construídos |
| Other | `kb/` PENDENTE DE REVISÃO; LC 224/2025 (aferição trimestral), regra da faixa 5 para ICMS/ISS e cumulatividade de serviços hospitalares não conferidas na fonte primária | Revisão contábil das regras é pré-requisito do piloto |
| Timeline | N/A (não informado) | — |

---

## Technical Context

| Aspect | Value | Notes |
|---|---|---|
| **Deployment Location** | `services/worker/src/worker/` (motor), `services/worker/rules/` (regras), `supabase/migrations/` (tabelas), `apps/web/src/app/(app)/cases/[id]/` (telas) | Extensão do monorepo; paths finais no Design |
| **KB Domains** | `kb/simples-nacional`, `kb/lucro-presumido`, `kb/lucro-real`, `kb/planejamento-comparativo`, `kb/documentos-fonte` | Fonte das regras e dos casos dourados |
| **IaC Impact** | Modify existing | Novas migrations no Supabase; mesmo container do worker |
| **LLM Prompts** | false | Motor determinístico sobre regras versionadas (Approach A); nenhum prompt, modelo ou geração de texto em runtime |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|---|---|---|---|
| A-001 | A regra de ICMS/ISS pela faixa 5, observada no PGDAS-D de 06/2026, vale para toda empresa na faixa 6 com sublimite ainda sem efeito | O teste de faixa 6 e o golden do Simples mudam | no (bate com a amostra, dispositivo não localizado) |
| A-002 | A majoração da LC 224/2025 é aferida trimestralmente sobre a receita acumulada no ano (R$ 1,25 mi por trimestre) | O teste da LC 224 e os valores do Presumido acima de R$ 5 mi mudam | no |
| A-003 | Receitas de serviços hospitalares permanecem no PIS/Cofins cumulativo mesmo no Lucro Real (Lei 10.833/2003, art. 10) | O teste de receita cumulativa no Real muda para clínicas | no (inferido do comparativo Econet) |
| A-004 | O RBT12 recalculado a partir da série 2.2 do PGDAS-D coincide com o RBT12 declarado | Se divergir, o motor precisa escolher a fonte e alertar | yes (06, 07 e 08/2026 da amostra) |
| A-005 | O usuário estará disponível no Build para aprovar o golden de Presumido e Real de 08/2026 | O golden de 08/2026 fica bloqueado até a aprovação | no |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---|---:|---|
| Problem | 3 | Dor, usuários e impacto claros e sustentados pelo Brainstorm e pelo PRD |
| Users | 3 | Analista, responsável técnico e administrador com dores específicas |
| Goals | 3 | MUST/SHOULD/COULD alinhados ao YAGNI e às decisões do Brainstorm |
| Success | 3 | Valores de referência ao centavo, tempo, reprodutibilidade, RLS e gate executável |
| Scope | 2 | Escopo e exclusões explícitos; a exatidão de três regras depende de revisão contábil (A-001 a A-003) |
| **Total** | **14/15** | |

Minimum to proceed: **12/15**.

---

## Open Questions

- (Não bloqueante) Conjunto exato de declarações de elegibilidade exibidas ao analista (lista das vedações do art. 17 da LC 123 a cobrir): detalhar no Design a partir de `kb/simples-nacional/patterns/testar-elegibilidade-simples.md`.
- (Não bloqueante) Formato do arquivo de regras (YAML ou JSON) e estrutura de versionamento: decisão do Design.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-24 | SDD Define by RDD | Initial version |

---

## Next Step

Execute o **SDD Design by RDD**.
