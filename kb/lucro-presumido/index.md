# Lucro Presumido

> **Do que trata:** apuração de IRPJ e CSLL por presunção sobre a receita (trimestral), PIS/Cofins cumulativo, limite de opção e a majoração de 10% da presunção criada pela LC 224/2025.
> **Para quem:** quem simula ou confere o Presumido no comparativo de regimes, e quem parametriza essas regras no motor.
> **Última revisão:** 2026-09-24
> **Revisado por:** PENDENTE DE REVISÃO

## Comece por aqui

Leia `concepts/base-presumida-e-lc224.md` — explica por que o Presumido ignora a margem real da empresa e o que mudou em 2026 para quem fatura acima de R$ 5 milhões. Depois execute `patterns/calcular-trimestre-presumido.md`.

## Conceitos — para entender

| Arquivo | Do que trata |
|---|---|
| [concepts/base-presumida-e-lc224.md](concepts/base-presumida-e-lc224.md) | Percentuais de presunção, adicional, receitas somadas integralmente e LC 224/2025 |
| [concepts/pis-cofins-cumulativo.md](concepts/pis-cofins-cumulativo.md) | Por que o Presumido paga 3,65% sem créditos, e quando isso pesa |

## Receitas — para fazer

| Arquivo | Resolve |
|---|---|
| [patterns/calcular-trimestre-presumido.md](patterns/calcular-trimestre-presumido.md) | Calcular IRPJ, adicional, CSLL, PIS e Cofins de um trimestre |

## Consulta rápida

- [quick-reference.md](quick-reference.md) — percentuais, alíquotas, limites e erros comuns

## O que este domínio NÃO cobre

- ICMS, IPI e ISS (dependem de UF, município e produto) — são somados no comparativo, mas as regras estão fora daqui.
- Encargos de folha: ver `../planejamento-comparativo/concepts/encargos-folha-por-regime.md`.
- Distribuição de lucros e JCP: ver `../planejamento-comparativo/concepts/remuneracao-socios-2026.md`.
- Transição para CBS/IBS a partir de 2027: ver `../reforma-tributaria/`.
- Atividades imobiliárias, factoring e instituições financeiras (regras específicas).

---

> **Responsabilidade:** a IA organizou e redigiu a partir de fontes públicas; quem responde pelo conteúdo é o profissional que revisar. A LC 224/2025 é recente, regulamentada por IN e questionada judicialmente — confira a situação vigente antes de usar em parecer.
