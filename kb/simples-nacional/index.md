# Simples Nacional

> **Do que trata:** como o Simples Nacional calcula o DAS (anexos, faixas, alíquota efetiva, repartição, Fator R) e quando a empresa pode ou não estar nele (limites, sublimites, vedações).
> **Para quem:** quem calcula, confere ou simula o Simples dentro do planejamento tributário — e quem implementa esse cálculo no motor.
> **Última revisão:** 2026-09-24
> **Revisado por:** PENDENTE DE REVISÃO

## Comece por aqui

Leia primeiro `concepts/aliquota-efetiva-e-reparticao.md`: quase todo erro de simulação do Simples vem de usar a alíquota nominal em vez da efetiva, ou de ignorar que a repartição entre tributos muda por faixa. Depois, `concepts/fator-r-e-anexos.md` se a empresa presta serviços.

Para executar, use `patterns/calcular-das-mensal.md`; para decidir se o Simples entra na comparação, `patterns/testar-elegibilidade-simples.md`.

## Conceitos — para entender

| Arquivo | Do que trata |
|---|---|
| [concepts/aliquota-efetiva-e-reparticao.md](concepts/aliquota-efetiva-e-reparticao.md) | Fórmula da alíquota efetiva, RBT12, repartição por tributo e o caso da faixa 6 |
| [concepts/fator-r-e-anexos.md](concepts/fator-r-e-anexos.md) | Como a atividade define o anexo e como o Fator R move serviços do Anexo V para o III |
| [concepts/limites-sublimites-e-exclusao.md](concepts/limites-sublimites-e-exclusao.md) | Teto de R$ 4,8 mi, sublimite de R$ 3,6 mi, excesso de 20% e efeitos no tempo |

## Receitas — para fazer

| Arquivo | Resolve |
|---|---|
| [patterns/calcular-das-mensal.md](patterns/calcular-das-mensal.md) | Calcular o DAS de uma competência, por atividade, com memória |
| [patterns/testar-elegibilidade-simples.md](patterns/testar-elegibilidade-simples.md) | Decidir se o Simples é juridicamente possível antes de simular custo |

## Consulta rápida

- [quick-reference.md](quick-reference.md) — tabelas dos Anexos I a V, limites e erros comuns

## O que este domínio NÃO cobre

- MEI (SIMEI) e seus valores fixos.
- Tabelas de repartição completas de todos os anexos e faixas (consultar Anexos da LC 123/2006).
- ICMS-ST, monofásico e ISS retido em detalhe por produto/município — aqui só o efeito no DAS.
- Efeitos da reforma tributária no Simples: ver `../reforma-tributaria/`.
- Comparação com outros regimes: ver `../planejamento-comparativo/`.

---

> **Responsabilidade:** a IA organizou e redigiu a partir de fontes públicas e das amostras do projeto; quem responde pelo conteúdo é o profissional que revisar. Enquanto o campo acima disser `PENDENTE DE REVISÃO`, trate números e condições como ponto de partida, não como parecer.
