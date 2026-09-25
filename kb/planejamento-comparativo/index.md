# Planejamento Tributário Comparativo

> **Do que trata:** o método para comparar Simples Nacional, Lucro Presumido e Lucro Real num exercício — elegibilidade primeiro, custo total depois (tributos sobre receita, renda e folha), remuneração dos sócios, ponto de virada e limites legais do planejamento.
> **Para quem:** o contador ou consultor que emite a recomendação, e quem implementa o motor de comparação e recomendação (ciclo 2 do projeto).
> **Última revisão:** 2026-09-24
> **Revisado por:** PENDENTE DE REVISÃO

## Comece por aqui

Leia `concepts/elegibilidade-antes-do-custo.md` — a regra que impede o erro crítico do PRD (recomendar regime impedido). Em seguida, `concepts/encargos-folha-por-regime.md`, porque a folha costuma decidir a comparação em serviços. Para executar, use `patterns/comparar-regimes-exercicio.md`.

## Conceitos — para entender

| Arquivo | Do que trata |
|---|---|
| [concepts/elegibilidade-antes-do-custo.md](concepts/elegibilidade-antes-do-custo.md) | Por que regime inelegível é "não aplicável", nunca "custo zero" |
| [concepts/encargos-folha-por-regime.md](concepts/encargos-folha-por-regime.md) | CPP, RAT, terceiros e FGTS em cada regime |
| [concepts/remuneracao-socios-2026.md](concepts/remuneracao-socios-2026.md) | Pró-labore × lucros × JCP depois da Lei 15.270/2025 e da LC 224/2025 |
| [concepts/elisao-x-evasao.md](concepts/elisao-x-evasao.md) | Onde termina o planejamento lícito |

## Receitas — para fazer

| Arquivo | Resolve |
|---|---|
| [patterns/comparar-regimes-exercicio.md](patterns/comparar-regimes-exercicio.md) | Montar o comparativo anual/mensal dos três regimes com recomendação explicável |
| [patterns/encontrar-ponto-de-virada.md](patterns/encontrar-ponto-de-virada.md) | Achar a margem, folha ou receita em que outro regime passa a vencer |

## Consulta rápida

- [quick-reference.md](quick-reference.md) — heurísticas de decisão, fatores de custo e erros comuns

## O que este domínio NÃO cobre

- Regras de cálculo de cada regime: ver `../simples-nacional/`, `../lucro-presumido/`, `../lucro-real/`.
- ICMS/ISS/IPI detalhados por UF, município e produto.
- Reorganizações societárias (cisão, holding), planejamento internacional e sucessório — fora do MVP pelo PRD.
- Desoneração da folha (CPRB) e seus cronogramas de reoneração — citada só como alerta.
- Efeitos de CBS/IBS a partir de 2027: ver `../reforma-tributaria/`.

---

> **Responsabilidade:** a IA organizou e redigiu; quem responde pela recomendação é o profissional habilitado que a aprova (PRD: 100% das recomendações com responsável e data). Heurísticas aqui são pontos de partida — a decisão sai da simulação com dados do cliente.
