# DEFINE: Planejamento Rápido (ciclo 5 do Planejamento Tributário)

> Novo tipo de dossiê que compara, para 2027, o Simples Nacional por dentro, o Simples por fora (híbrido) e o Lucro Presumido a partir do faturamento dos últimos 12 meses, da folha e da DRE (PDF ou digitação), com anexo sugerido pelo CNAE consultado na Receita e a faixa do Simples informada.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | PLANEJAMENTO_RAPIDO |
| **Date** | 2026-09-26 |
| **Author** | SDD Define by RDD |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O escritório só consegue planejar o regime de empresas que entregam o pacote completo (PGDAS-D, folha, DRE e balancete, com conciliações); quando há apenas o faturamento dos últimos 12 meses, a folha e a DRE — em PDF ou nem isso —, a comparação entre Simples por dentro, Simples por fora e Presumido para 2027 é feita fora do sistema, sem memória de cálculo, sem aprovação do responsável técnico e sem relatório rastreável.

---

## Target Users

| User | Role | Pain Point |
|---|---|---|
| Analista do escritório | Cria o dossiê rápido, envia ou digita faturamento, folha e DRE, confirma premissas e pede a projeção de 2027 | Não consegue usar o sistema sem PGDAS-D e balancete |
| Responsável técnico | Revisa e aprova a recomendação | Precisa de um comparativo rastreável (origem PDF × digitado, CNAE, faixa) mesmo com entrada simplificada |
| Cliente do escritório | Recebe o PDF da recomendação de 2027 | Decide entre Simples por dentro, por fora e Presumido |

---

## Goals

| Priority | Goal |
|---|---|
| **MUST** | Novo tipo de dossiê "planejamento rápido" com o mesmo ciclo de vida do dossiê completo: upload/digitação → validações → homologação (snapshot com hash) → premissas → projeção de 2027 → aprovação do responsável técnico → PDF |
| **MUST** | Parser da Declaração de Faturamento (layout da amostra `RBT12.pdf`): CNPJ, período, 12 meses e Total Geral, com origem (página e posição) de cada valor; validações: soma dos meses = Total Geral, 12 meses consecutivos, CNPJ do dossiê |
| **MUST** | Folha e DRE pelos parsers Alterdata existentes, de 1 a 12 meses |
| **MUST** | Digitação manual mês a mês quando não houver PDF — faturamento; folha (salários dos empregados, pró-labore, autônomos); DRE (receita bruta, outras receitas, resultado) — registrando quem digitou e quando; mês/documento com PDF só muda por ajuste justificado |
| **MUST** | CNAE principal e secundários obtidos pela automação n8n (MCP, ferramenta `Consultar_CNPJ`); se ela falhar, o analista digita o CNAE; só CNAE, descrição e razão social são guardados (sem sócios) |
| **MUST** | Tabela CNAE → anexo (I a V, com Fator R e vedações) como regra versionada, `verificado: false` até a revisão contábil; o perfil da atividade é sugerido pela tabela e confirmado pelo analista |
| **MUST** | Premissas do dossiê rápido: perfil/anexo, % da receita com ICMS-ST, % com PIS/Cofins monofásico e ICMS no regime normal, além das premissas de 2027 do ciclo 4 (alíquotas de CBS/IBS, crescimento, base de créditos) |
| **MUST** | Projeção de 2027 = 2026 montado (meses com folha e DRE realizados; demais meses da declaração estimados pelo faturamento; meses após o último faturamento projetados pela média) deslocado com o crescimento, pelo motor do ciclo 4 sem alteração de regra |
| **MUST** | Comparativo com três alternativas — Simples por dentro, Simples por fora (híbrido) e Lucro Presumido —, sem Lucro Real, com sensibilidade e recomendação |
| **MUST** | Tela, memória e PDF informam, para o Simples, a faixa do anexo pelo RBT12, a alíquota nominal, a parcela a deduzir e a alíquota efetiva |
| **MUST** | Golden do planejamento rápido da amostra aprovado pelo usuário no build |
| **SHOULD** | Distribuir a receita entre o CNAE principal e os secundários por premissa (percentual), quando a empresa tiver atividades em anexos diferentes |
| **COULD** | Converter um dossiê rápido em dossiê completo depois, reaproveitando os documentos |

---

## Success Criteria

- [ ] A Declaração de Faturamento da amostra é extraída com 100% dos 12 meses, soma = Total Geral R$ 3.719.883,51 e CNPJ 37704456000142.
- [ ] 100% dos valores do snapshot do dossiê rápido têm origem (PDF com página ou digitação com usuário e data/hora).
- [ ] Projeção + sensibilidade + recomendação de 2027 do dossiê rápido concluídas em ≤ 60 s.
- [ ] Comparativo com exatamente 3 alternativas (SIMPLES, SIMPLES_HIBRIDO, PRESUMIDO) e 0 linhas de Lucro Real.
- [ ] CNAE 4744-0/01 da amostra sugere o Anexo I; 100% dos meses do Simples mostram faixa, alíquota nominal, parcela a deduzir e efetiva.
- [ ] 0 dados de sócios gravados a partir da consulta de CNPJ.
- [ ] Goldens `motor_202608`, `motor_202606_08`, `decisao_2026` e `decisao_2027` continuam reproduzidos exatamente (100%).
- [ ] Golden do planejamento rápido aprovado pelo usuário no build.

---

## Acceptance Tests

| ID | Pattern | Criterion (EARS) | Gate (`kind`) |
|---|---|---|---|
| AT-501 | Event-driven | **When** a Declaração de Faturamento da amostra é enviada a um dossiê rápido, the system **shall** classificá-la, extrair CNPJ, período e os 12 meses com página de origem e aprovar a validação "soma dos meses = Total Geral" | test |
| AT-502 | Unwanted | **If** a soma dos meses da declaração difere do Total Geral além de R$ 0,01, **then** the system **shall** marcar a validação como falha e bloquear a homologação até um ajuste justificado | test |
| AT-503 | Unwanted | **If** o CNPJ da declaração difere do CNPJ do dossiê, **then** the system **shall** marcar o arquivo como CNPJ divergente | test |
| AT-504 | Unwanted | **If** o dossiê rápido não tem 12 meses consecutivos de faturamento (PDF ou digitados), **then** the system **shall** bloquear a homologação informando os meses faltantes | test |
| AT-505 | Event-driven | **When** o analista digita faturamento, folha ou DRE de um mês sem PDF, the system **shall** gravar o valor com o usuário e a data/hora e usá-lo no snapshot homologado | test |
| AT-506 | Unwanted | **If** o analista tenta digitar um valor de mês/documento que já tem PDF extraído, **then** the system **shall** recusar a digitação e indicar o ajuste justificado | test |
| AT-507 | Unwanted | **If** o dossiê rápido não tem ao menos um mês de folha e um mês de DRE (PDF ou digitados), **then** the system **shall** bloquear a homologação | test |
| AT-508 | Event-driven | **When** o CNAE da empresa é consultado, the system **shall** chamar a ferramenta `Consultar_CNPJ` da automação n8n e gravar CNAE principal, secundários, descrições e razão social, sem dados de sócios | test |
| AT-509 | Unwanted | **If** a automação n8n falha, expira ou responde sem CNAE, **then** the system **shall** avisar e permitir que o analista digite o CNAE principal | test |
| AT-510 | Event-driven | **When** as premissas do dossiê rápido são geradas, the system **shall** sugerir o perfil da atividade pela tabela CNAE → anexo (CNAE 4744-0/01 → Anexo I), pendente de confirmação | test |
| AT-511 | Unwanted | **If** o CNAE não está na tabela, **then** the system **shall** deixar o perfil sem sugestão e bloquear a recomendação até o analista escolher o anexo | test |
| AT-512 | Event-driven | **When** a Projeção 2027 de um dossiê rápido é pedida, the system **shall** calcular Simples por dentro, Simples por fora e Lucro Presumido, sem Lucro Real, com a base de 2026 deslocada pelo crescimento confirmado | test |
| AT-513 | Event-driven | **When** o Simples é calculado no dossiê rápido, the system **shall** exibir na tela, na memória e no PDF a faixa do anexo pelo RBT12 do mês, a alíquota nominal, a parcela a deduzir e a alíquota efetiva | test |
| AT-514 | Unwanted | **If** o RBT12 ultrapassa R$ 4.800.000,00, **then** the system **shall** marcar o Simples por dentro e por fora como inelegíveis e recomendar entre as alternativas restantes | test |
| AT-515 | Unwanted | **If** perfil da atividade, % com ST, % monofásico ou ICMS no regime normal estão pendentes, **then** the system **shall** marcar a recomendação como bloqueada, com prévia incompleta | test |
| AT-516 | Event-driven | **When** a Projeção 2027 de um dossiê rápido é pedida, the system **shall** concluir projeção, sensibilidade e recomendação em até 60 s | test |
| AT-517 | Event-driven | **When** uma recomendação de dossiê rápido aprovada é emitida, the system **shall** gerar o PDF identificado como "planejamento rápido", com o CNAE, a faixa do Simples, as três alternativas e a origem dos dados (PDF × digitado) | test |
| AT-518 | Event-driven | **When** o motor projeta 2027 com as amostras do dossiê rápido e as premissas do golden, the system **shall** reproduzir exatamente o golden aprovado | test |
| AT-519 | Non-regression | The system **shall continue to** reproduzir exatamente os goldens `motor_202608`, `motor_202606_08`, `decisao_2026` e `decisao_2027` e o fluxo do dossiê completo | test |

---

## Clarifications

### Session 2026-09-26

- [x] (NFRs) Tempo máximo da projeção do dossiê rápido → até 60 s (1a); integrado em Success Criteria e AT-516
- [x] (Data model) Campos da digitação manual → mês a mês: folha (salários dos empregados, pró-labore, autônomos) e DRE (receita bruta, outras receitas, resultado) (2a); integrado em Goals e AT-505
- [x] (Scope) Perfil da atividade sem PGDAS-D → sugerido a partir do CNAE; o Simples é calculado pelo anexo e pelo RBT12 informando a faixa (3); integrado em Goals, AT-510, AT-513
- [x] (Integrations) Origem do CNAE → consulta automática pela automação n8n já existente (4c); integrado em Goals e AT-508
- [x] (Scope) Cobertura da tabela CNAE → anexo → todos os anexos, com Fator R e vedações (5b); integrado em Goals e Assumptions
- [x] (Data model) CNAE principal da amostra → 4744-0/01 (6); integrado em Success Criteria e AT-510
- [x] (Integrations) Contrato da automação → `https://webhook.dieksonbernardes.com.br/mcp/consulta-cnpj`, servidor MCP do n8n (MCP Server Trigger, HTTP com streaming), sem autenticação, ferramenta `Consultar_CNPJ` com entrada `{"cnpj": "<14 dígitos>"}`, dados da BrasilAPI (verificado por `initialize` + `tools/list`, sem consultar CNPJ) (7); integrado em Constraints e Assumptions
- [x] (Edge cases) Falha da automação → aviso e CNAE digitado pelo analista (8a); integrado em AT-509

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

- Lucro Real no dossiê rápido.
- Comparativo de 2026 no dossiê rápido.
- Outros layouts de Declaração de Faturamento; folha e DRE de outros ERPs; entrada por XLSX/CSV.
- Conciliações R1–R7 no dossiê rápido (dependem de PGDAS-D e balancete).
- Mix de vendas B2B × consumidor final, transição 2029–2033, Imposto Seletivo, ZFM, alíquotas por NCM, split payment e opção semestral do híbrido.
- Consulta de CEP e demais dados cadastrais além de CNAE e razão social.

---

## Constraints

| Type | Constraint | Impact |
|---|---|---|
| Technical | Motor e regras tributárias de 2026/2027 não mudam; a tabela CNAE → anexo é regra nova e versionada | Goldens anteriores protegidos; dossiê rápido entra pelo snapshot |
| Technical | Automação n8n é um servidor MCP sem autenticação, com dados da BrasilAPI | Chamada só pelo servidor (worker/web server), com timeout; endereço em variável de ambiente; resposta de sócios descartada |
| Technical | Regras de 2027 e a tabela CNAE → anexo seguem `verificado: false` | Ressalva no PDF; revisão contábil antes do uso com clientes |
| Resource | Uma única amostra de Declaração de Faturamento (layout NTW) e folha/DRE só no layout Alterdata | Parser preso a esse layout; outros layouts falham como "não reconhecido" |
| Other | `docs/Amostras/RBT12.pdf` contém CPF e CRC dos signatários | Fora do Git; golden sem dados pessoais |

---

## Technical Context

| Aspect | Value | Notes |
|---|---|---|
| **Deployment Location** | `services/worker` (parser, snapshot, premissas, projeção, consulta n8n), `supabase/migrations` (tipo de dossiê, tipo de documento, valores digitados, CNAE), `apps/web` (criação do dossiê rápido, digitação, CNAE, faixa) | Mesma arquitetura dos ciclos 1–4 |
| **KB Domains** | `simples-nacional`, `lucro-presumido`, `reforma-tributaria`, `documentos-fonte` | Anexos, faixas, sublimite, Fator R, vedações, CBS/IBS 2027 |
| **IaC Impact** | Modify existing | Migration nova no Supabase; variável de ambiente com o endereço da automação n8n; imagem do worker sem mudança estrutural |
| **LLM Prompts** | false | A automação é chamada como ferramenta MCP determinística (consulta de CNPJ); não há prompt de LLM em runtime |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|---|---|---|---|
| A-501 | A ferramenta `Consultar_CNPJ` devolve o JSON da BrasilAPI com `cnae_fiscal`, `cnae_fiscal_descricao` e `cnaes_secundarios` | Mapeamento da resposta muda no Build | no |
| A-502 | Tabela CNAE → anexo montada a partir da LC 123/2006 e da Resolução CGSN 140/2018 via fontes secundárias | Anexo sugerido errado; mitigado pela confirmação do analista e `verificado: false` | no |
| A-503 | Sem distribuição informada, 100% da receita é atribuída ao CNAE principal | Empresas com atividades em anexos diferentes calculadas num só anexo | no |
| A-504 | A Declaração de Faturamento lista 12 meses consecutivos e o Total Geral no layout da amostra | Parser falha em declarações com outro formato | yes (amostra) |
| A-505 | O RBT12 do primeiro mês projetado vem da série de faturamento da declaração, como hoje vem da série do PGDAS-D | Faixa e alíquota efetiva dos primeiros meses diferentes | no |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---|---:|---|
| Problem | 3 | Pedido específico do usuário com fluxo validado em dois checkpoints |
| Users | 3 | Analista, responsável técnico e cliente, como nos ciclos 3–4 |
| Goals | 3 | MUST/SHOULD/COULD com entradas, integração, regra nova e saídas definidas |
| Success | 3 | Metas numéricas (60 s, 3 alternativas, 12 meses, total da amostra, 0 sócios gravados) |
| Scope | 2 | Fronteiras claras; cobertura exata da tabela CNAE → anexo depende da pesquisa no Design |
| **Total** | **14/15** | |

Minimum to proceed: **12/15**.

---

## Open Questions

- Não bloqueante: formato exato da resposta de `Consultar_CNPJ` (A-501) — conferir no Design com uma consulta da amostra, descartando os dados de sócios.
- Não bloqueante: a automação n8n não exige autenticação; recomendável proteger o endpoint com token antes de produção (fora do sistema de planejamento).

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-26 | SDD Define by RDD | Initial version |

---

## Next Step

Execute o **SDD Design by RDD**.
