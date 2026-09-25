# Anexos por atividade e Fator R

> **O que é:** a regra que decide em qual anexo cada receita é tributada — e o Fator R, razão folha/receita que move certas atividades de serviço entre o Anexo V (mais caro) e o Anexo III.
> **Fonte:** LC 123/2006, art. 18, §§ 5º-B a 5º-M e § 24 (redação LC 155/2016); valores conferidos em fontes secundárias em 2026-09-24 — confirmar na norma a lista de atividades de cada parágrafo.

## Por que isto existe

O Simples tributa diferentemente comércio, indústria e serviços, e entre serviços distingue os intensivos em mão de obra. O Fator R premia quem tem folha alta: sem ele, um serviço intelectual com pouca folha paga o Anexo V (15,5% na 1ª faixa) em vez do III (6%).

## Como funciona

**Anexo pela atividade (não pelo CNAE isolado):**

| Anexo | Atividades típicas |
|---|---|
| I | Comércio (revenda de mercadorias) |
| II | Indústria (fabricação) |
| III | Serviços em geral (§ 5º-B, § 5º-D), p. ex. manutenção, agências, academias |
| IV | Construção civil, vigilância, limpeza, advocacia (§ 5º-C) — CPP fora do DAS |
| V | Serviços intelectuais/técnicos do § 5º-I (engenharia, TI, publicidade, auditoria, consultoria etc.), sujeitos ao Fator R |

Uma mesma empresa pode ter receitas em vários anexos; cada receita usa o anexo da sua atividade, mas **a faixa é definida pelo RBT12 total** da empresa.

**Fator R:**

`r = folha de salários dos 12 meses anteriores ao PA ÷ receita bruta dos 12 meses anteriores`

- Folha inclui salários, pró-labore, FGTS e CPP recolhida (conforme § 24) — **não** inclui distribuição de lucros.
- Atividades do § 5º-I: `r ≥ 28%` → Anexo III; `r < 28%` → Anexo V.
- É recalculado **todo mês**; a empresa pode oscilar entre os anexos ao longo do ano.

## Exemplo (fictício)

Consultoria, RBT12 R$ 600.000, folha 12 meses R$ 180.000 → r = 30%:

| Anexo | Cálculo | Efetiva |
|---|---|---|
| III (r ≥ 28%) | (600.000 × 13,5% − 17.640) ÷ 600.000 | 10,56% |
| V (se r < 28%) | (600.000 × 19,5% − 9.900) ÷ 600.000 | 17,85% |

Diferença de 7,29 p.p. sobre a receita — muitas vezes maior do que o custo de aumentar o pró-labore.

## O que costuma ser confundido

| Isto | Não é isto |
|---|---|
| Fator R decide entre V e III | Fator R vale para todas as atividades de serviço |
| Folha de 12 meses anteriores ao PA | Folha do próprio mês |
| Pró-labore entra na folha | Lucros distribuídos entram na folha |
| Anexo IV paga CPP por fora | Anexo IV é "mais barato" porque a nominal é menor |
| Faixa pelo RBT12 da empresa toda | Faixa separada por atividade |

## Quando isto importa na prática

- **Planejamento de pró-labore:** elevar o pró-labore para atingir 28% é planejamento lícito, mas o custo (INSS 11% do sócio, IRPF) precisa entrar na conta — ver `../../planejamento-comparativo/concepts/remuneracao-socios-2026.md`.
- **Projeção:** um mês de folha baixa (férias, desligamento) pode derrubar o r abaixo de 28% vários meses depois.
- **Motor:** a memória mensal deve mostrar folha, receita, r e o anexo resultante (critério de aceite do PRD).
- No PGDAS-D, a seção 2.3 lista a folha dos meses anteriores e a 2.4 mostra o Fator r ("Não se aplica" quando não há atividade sujeita).

## Relacionados

- [aliquota-efetiva-e-reparticao.md](aliquota-efetiva-e-reparticao.md)
- [../../planejamento-comparativo/concepts/encargos-folha-por-regime.md](../../planejamento-comparativo/concepts/encargos-folha-por-regime.md)
