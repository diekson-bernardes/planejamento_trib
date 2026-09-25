# DEFINE: Decisão Tributária (ciclo 3 do Planejamento Tributário)

> Projeção do exercício 2026 pelo motor, sensibilidade com ponto de virada, recomendação explicável com aprovação do responsável técnico e PDF executivo imutável.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | DECISAO_TRIBUTARIA |
| **Date** | 2026-09-25 |
| **Author** | SDD Define by RDD |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O escritório compara Simples, Presumido e Real apenas no período realizado (ciclo 2) e não consegue emitir ao cliente, com aprovação do responsável técnico, uma recomendação explicável do exercício que mostre a projeção anual, o ponto de virada de cada variável relevante e as ressalvas — hoje isso exige planilhas paralelas sem rastreabilidade.

---

## Target Users

| User | Role | Pain Point |
|---|---|---|
| Analista do escritório | Elabora a projeção, ajusta orçamento e envia a recomendação para revisão | Precisa projetar o exercício e testar sensibilidade sem planilhas paralelas |
| Responsável técnico | Contador (nome + CRC) que revisa, aprova ou devolve e assina a recomendação | Precisa revisar premissas, ressalvas e resultado antes de chegar ao cliente, com segregação de quem elaborou |
| Administrador do escritório | Configura o limiar de inconclusivo e marca quais membros são responsáveis técnicos | Não há papel nem política configurável para aprovação |
| Cliente do escritório | Recebe o PDF executivo | Precisa saber qual regime, quanto economiza e em que condições a recomendação deixa de valer |

---

## Goals

| Priority | Goal |
|---|---|
| **MUST** | Projeção do exercício 2026 (jan–dez) calculada pelas mesmas funções do motor do ciclo 2: jan–mai pelas séries do PGDAS-D (receita e folha) com demais campos proporcionais à receita, jun–ago realizado, set–dez por média simples dos meses completos ou por orçamento informado; cada mês marcado como realizado, estimado ou projetado |
| **MUST** | Projeção imutável, idempotente e com memória linha a linha (regra, versão, origem), no mesmo padrão das simulações do ciclo 2 |
| **MUST** | Sensibilidade sobre 5 variáveis (receita, margem antes de IRPJ/CSLL, folha/receita, créditos de PIS/Cofins, ICMS/ISS): ponto de virada ou "sem virada no intervalo", distância e robustez (> 20% robusta, 5–20% atenção, < 5% frágil); cruzamento de limite de elegibilidade reportado como limite jurídico |
| **MUST** | Recomendação com três estados: recomendado (diferença entre os dois primeiros elegíveis ≥ limiar), inconclusivo (< limiar), bloqueado (dado crítico ausente, com prévia marcada "incompleta") |
| **MUST** | Explicação da recomendação: "recomendamos X porque…", três fatores econômicos, economia absoluta e percentual vs. regime atual (Simples, pelo PGDAS-D) e vs. segundo colocado, carga sobre consumo, renda e folha, ressalvas e premissas |
| **MUST** | Papel de responsável técnico (nome + CRC) marcado pelo admin; fluxo rascunho → em revisão → aprovado / devolvido → emitido; quem elabora não aprova |
| **MUST** | PDF executivo gerado somente de recomendação aprovada: formato do SPTE (resultado mensal por regime, observações, comparativo final) + seções do PRD (data-base normativa, premissas, ressalvas, sensibilidade, responsável técnico e registro de aprovação); imutável, com SHA-256 |
| **MUST** | Golden da Projeção 2026 da amostra aprovado pelo usuário durante o build, mais casos construídos (recomendado, bloqueado, inelegível) |
| **SHOULD** | Limiar de inconclusivo configurável por escritório (padrão 5% do custo do regime vencedor) |
| **SHOULD** | Custo de conformidade informado por regime como premissa e exibido separado, sem alterar o ranking |
| **COULD** | XLSX da memória da projeção e da sensibilidade (reuso da exportação do ciclo 2) |

---

## Success Criteria

- [ ] Projeção 2026 da amostra (12 competências) reproduz exatamente o golden aprovado: totais por regime e por mês, status da recomendação e ponto de virada de cada uma das 5 variáveis.
- [ ] Mesmas entradas (snapshot, premissas, regras, método de projeção) → mesmo `result_hash` em 100% das reexecuções; nenhuma projeção duplicada.
- [ ] 100% das linhas da projeção têm regra com versão e origem (realizado, estimado ou projetado).
- [ ] Projeção + sensibilidade + recomendação concluídas em ≤ 60 s para um dossiê de até 12 competências.
- [ ] 0 aprovações por quem não é responsável técnico ou por quem elaborou a recomendação (verificado em pgTAP).
- [ ] 100% dos PDFs emitidos com SHA-256 registrado e conteúdo inalterado após nova alteração de premissas.
- [ ] Goldens do ciclo 2 (`motor_202608`, `motor_202606_08`) continuam reproduzidos exatamente.

---

## Acceptance Tests

| ID | Pattern | Criterion (EARS) | Gate (`kind`) |
|---|---|---|---|
| AT-201 | Event-driven | **When** o analista pede a Projeção 2026 de um dossiê com simulação concluída, the system **shall** montar os 12 meses de jan a dez/2026 e marcar cada mês como realizado, estimado ou projetado | test |
| AT-202 | State-driven | **While** um mês de 2026 anterior à primeira competência completa não tem documentos, the system **shall** usar receita e folha das séries do PGDAS-D e estimar lucro, créditos, ICMS/ISS e outras receitas em proporção à receita, marcando-os como premissa | test |
| AT-203 | Event-driven | **When** o analista informa orçamento (receita, margem ou folha) para um mês projetado, the system **shall** usar o valor informado no lugar da média e marcar a origem como orçamento | test |
| AT-204 | Unwanted | **If** o analista altera um valor sugerido da projeção sem justificativa de ao menos 5 caracteres, **then** the system **shall** recusar a alteração | test |
| AT-205 | Event-driven | **When** a projeção é recalculada com o mesmo snapshot, premissas, regras e método, the system **shall** reutilizar a projeção existente com o mesmo `result_hash` | test |
| AT-206 | Where | **Where** a receita acumulada projetada cruza o sublimite, o teto do Simples, o limite de R$ 78 mi do Presumido ou o limite da LC 224, the system **shall** aplicar o efeito no mês determinado pela regra e exibir o alerta correspondente | test |
| AT-207 | Event-driven | **When** a sensibilidade roda, the system **shall** informar para cada uma das 5 variáveis o valor do cenário base, o ponto de virada (ou "sem virada no intervalo"), a distância percentual e a robustez (> 20% robusta, 5–20% atenção, < 5% frágil) | test |
| AT-208 | Where | **Where** a variação de uma variável torna um regime inelegível, the system **shall** reportar o valor como limite jurídico e não como ponto de virada de custo | test |
| AT-209 | Event-driven | **When** a diferença entre os dois primeiros regimes elegíveis é maior ou igual ao limiar do escritório, the system **shall** emitir status "recomendado" com o regime, o texto "recomendamos X porque…", três fatores, a economia vs. regime atual e vs. segundo colocado e a carga sobre consumo, renda e folha | test |
| AT-210 | Where | **Where** a diferença entre os dois primeiros regimes elegíveis é menor que o limiar do escritório, the system **shall** emitir status "resultado inconclusivo" destacando a sensibilidade | test |
| AT-211 | Unwanted | **If** falta dado crítico (nenhuma competência completa, série do PGDAS-D incompleta ou premissa pendente), **then** the system **shall** bloquear a recomendação, mostrar prévia marcada "incompleta" e impedir o envio para revisão | test |
| AT-212 | Unwanted | **If** um regime está inelegível ou "não calculado", **then** the system **shall** excluí-lo do ranking e exibir o motivo e a regra | test |
| AT-213 | Event-driven | **When** o custo de conformidade é informado por regime, the system **shall** exibi-lo separado do custo tributário sem alterar o ranking | test |
| AT-214 | Event-driven | **When** o admin define o limiar e marca um membro como responsável técnico com nome e CRC, the system **shall** gravar a configuração e registrá-la na auditoria | test |
| AT-215 | Unwanted | **If** um usuário que não é responsável técnico tenta aprovar uma recomendação, **then** the system **shall** recusar a ação | test |
| AT-216 | Unwanted | **If** o responsável técnico tenta aprovar uma recomendação que ele mesmo elaborou, **then** the system **shall** recusar a ação | test |
| AT-217 | Event-driven | **When** o responsável técnico devolve uma recomendação com comentário de ao menos 5 caracteres, the system **shall** voltá-la para rascunho e registrar o evento com autor, data e comentário | test |
| AT-218 | Event-driven | **When** uma recomendação aprovada é emitida, the system **shall** gerar o PDF com resultado mensal por regime, observações, comparativo, sensibilidade, recomendação, data-base normativa, premissas, ressalvas (regras não conferidas e regras de 2027) e responsável técnico com CRC e data de aprovação, gravando seu SHA-256 | test |
| AT-219 | Unwanted | **If** uma premissa muda depois da aprovação, **then** the system **shall** voltar a recomendação para rascunho e manter o PDF já emitido inalterado e disponível | test |
| AT-220 | Unwanted | **If** um usuário de outro escritório tenta ler projeções, sensibilidades, recomendações ou PDFs, **then** the system **shall** negar via RLS | test |
| AT-221 | Event-driven | **When** a projeção de um dossiê de até 12 competências é pedida, the system **shall** concluir projeção, sensibilidade e recomendação em até 60 s | test |
| AT-222 | Event-driven | **When** o motor projeta 2026 com as amostras de 06–08/2026, the system **shall** reproduzir exatamente o golden aprovado (totais por regime e mês, status e pontos de virada) | test |
| AT-223 | Non-regression | The system **shall continue to** reproduzir exatamente os goldens `motor_202608` e `motor_202606_08` do período realizado | test |

---

## Clarifications

### Session 2026-09-25

- [x] (NFRs) Tempo máximo de projeção + sensibilidade + recomendação para até 12 competências? → até 60 s (estimativa de 5–15 s com ≈ 40 ms por cálculo); integrado em Success Criteria e AT-221
- [x] (Done signal) Caso de referência do aceite? → golden da Projeção 2026 da amostra aprovado pelo usuário durante o build, mais casos construídos (recomendado, bloqueado, inelegível); integrado em Goals, Success Criteria e AT-222
- [x] (Data model / UX flow) Quem configura limiar e papel; o responsável técnico pode elaborar? → o admin do escritório define o limiar e marca responsáveis técnicos (nome + CRC); o responsável técnico pode elaborar, mas nunca aprova a própria elaboração; o admin só aprova se também for responsável técnico; integrado em Target Users, Goals e AT-214 a AT-216
- Varredura das 9 categorias: Scope (Clear: YAGNI do Brainstorm), Data model (Clear após clarificação: projeções, sensibilidades, recomendações, eventos do fluxo, papel e configuração do escritório), UX flow (Clear: projeção → sensibilidade → recomendação → revisão → aprovação → emissão), NFRs (Clear após clarificação), Integrations (Clear: somente motor, snapshot e fila existentes), Edge cases (Clear: AT-204, AT-206, AT-208, AT-211, AT-212, AT-215, AT-216, AT-219, AT-220), Constraints (Clear), Terminology (Clear: "realizado" = competência completa homologada; "estimado" = mês com dado do PGDAS-D e demais campos proporcionais; "projetado" = mês sem documento, por média ou orçamento; "ponto de virada" = valor da variável em que o primeiro colocado muda; "limite jurídico" = valor em que a elegibilidade muda), Done signal (Clear após clarificação).

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

- Projeção por sazonalidade (exige histórico ≥ 24 meses).
- Cenários conservador / base / expansão.
- Variáveis de sensibilidade de mix de atividades, B2B/B2C e benefícios fiscais.
- Resultado líquido e fluxo de caixa após tributos.
- Assinatura eletrônica do PDF (o PDF identifica o responsável e registra a aprovação com data e hash).
- Duplicar cenário e comparar versões (RF-14) e painel de pendências e alertas (RF-15).
- Projeção de 2027 e regras da Reforma Tributária (CBS/IBS).
- Custo de conformidade somado ao ranking.

---

## Constraints

| Type | Constraint | Impact |
|---|---|---|
| Technical | Somente regras do exercício 2026 (versão 2026.1.0); o PDF informa que 2027 terá regras de transição da Reforma ainda não calculadas | Projeção restrita a jan–dez/2026 |
| Technical | Reutilizar as funções do motor do ciclo 2, sem alterar o cálculo do período realizado | Goldens do ciclo 2 são regressão obrigatória |
| Technical | Isolamento por escritório (RLS), logs sem dados sensíveis, PDFs no Storage privado | Novas tabelas e caminhos de Storage com RLS e testes pgTAP |
| Technical | Verify Gate `npm run verify` ampliado com os testes do ciclo 3 | Build precisa incluir pytest, pgTAP e testes web novos no gate existente |
| Resource | Amostra com 3 competências completas (06–08/2026) e séries do PGDAS-D; jan–mai sem DRE/balancete | Lucro, créditos, ICMS/ISS e outras receitas de jan–mai estimados e marcados como premissa |
| Resource | Sem ground truth externo de projeção; SPTE usado só como referência de formato | Aceite por golden aprovado pelo usuário e casos construídos |
| Other | Regras `verificado: false` (LC 224 trimestral, ICMS/ISS da faixa 6 pela faixa 5, cumulatividade hospitalar) | Aparecem como ressalva no PDF |
| Timeline | N/A (não informado) | — |

---

## Technical Context

| Aspect | Value | Notes |
|---|---|---|
| **Deployment Location** | `services/worker/src/worker/engine/` (projeção, sensibilidade, recomendação), `services/worker/src/worker/pipeline.py` (jobs), `supabase/migrations/` (tabelas, papel, RLS, RPCs), `apps/web/src/app/(app)/cases/[id]/planning/` (telas) | Mesmo monorepo e padrões dos ciclos 1 e 2 |
| **KB Domains** | `planejamento-comparativo` (ponto de virada, comparação por exercício), `simples-nacional` (limites, sublimite, descontinuidades), `lucro-presumido` (LC 224), `lucro-real` | Método de virada e robustez da KB |
| **IaC Impact** | Modify existing | Imagem do worker precisa da dependência de geração de PDF; bucket `documents` ganha caminho de relatórios protegido |
| **LLM Prompts** | false | Texto da recomendação é montado por regras determinísticas a partir do cálculo; nenhum provedor/modelo de LLM, prompt ou RAG no Brainstorm |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|---|---|---|---|
| A-201 | Lucro, créditos de PIS/Cofins, ICMS/ISS e outras receitas de jan–mai/2026 são proporcionais à receita na mesma razão média dos meses completos | Projeção de Presumido e Real de jan–mai muda | yes (Brainstorm, Q2) |
| A-202 | Média simples dos meses completos representa set–dez quando não há orçamento (sem sazonalidade forte) | Projeção de set–dez muda; orçamento corrige | yes (Brainstorm, Q2 e PRD §9) |
| A-203 | RBT12 dos meses de jan–mai/2026 pode ser completado com as séries disponíveis do PGDAS-D (meses anteriores a 06/2025 ausentes estimados pela média mensal da série) | Faixa do Simples de jan–mai pode mudar | no |
| A-204 | Faixas de robustez > 20% / 5–20% / < 5% (sugestão da KB) valem como padrão fixo no ciclo 3 | Classificação de robustez muda | no (KB indica política configurável; limiar configurável é só o de inconclusivo) |
| A-205 | Intervalos de variação da sensibilidade (ex.: margem 0–40%, folha/receita 10–45%, KB) são suficientes para localizar a virada nos casos do escritório | "Sem virada no intervalo" em casos reais que teriam virada | no |
| A-206 | Regime atual do cliente é o Simples Nacional, identificado pelo PGDAS-D do snapshot | Economia vs. regime atual calculada contra o regime errado | yes (amostra) |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---|---:|---|
| Problem | 3 | Dor, usuários e impacto explícitos no Brainstorm |
| Users | 3 | Analista, responsável técnico, admin e cliente com papéis definidos após clarificação |
| Goals | 3 | MUST/SHOULD/COULD alinhados ao Brainstorm e ao YAGNI |
| Success | 3 | Critérios numéricos (60 s, 100%, 0 aprovações indevidas, golden exato) |
| Scope | 2 | Fronteiras claras; intervalos da sensibilidade e RBT12 de jan–mai ficam como hipóteses para o Design |
| **Total** | **14/15** | |

Minimum to proceed: **12/15**.

---

## Open Questions

- Não bloqueante: intervalos exatos de variação de cada variável da sensibilidade e passo de busca (A-205) — decidir no Design com base na KB.
- Não bloqueante: método de completar o RBT12 de jan–mai/2026 (A-203) — decidir no Design e expor como premissa.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-25 | SDD Define by RDD | Initial version |

---

## Next Step

Execute o **SDD Design by RDD**.
