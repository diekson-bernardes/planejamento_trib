# Reforma Tributária do Consumo

> **Do que trata:** a substituição de PIS, Cofins, IPI, ICMS e ISS por CBS, IBS e Imposto Seletivo (EC 132/2023, LC 214/2025) — calendário de transição 2026–2033 e o que muda para o planejamento, em especial para optantes do Simples e seus clientes B2B.
> **Para quem:** quem projeta exercícios de 2027 em diante e quem parametriza os módulos CBS/IBS do motor (PRD §8.5).
> **Última revisão:** 2026-09-24
> **Revisado por:** PENDENTE DE REVISÃO

## Comece por aqui

Leia `concepts/calendario-transicao.md` para saber qual tributo vale em qual ano (o motor precisa disso por exercício). Se o cliente é do Simples, leia `concepts/simples-na-reforma.md` e execute `patterns/avaliar-opcao-regime-regular-simples.md` — **a primeira janela de opção vence em setembro de 2026**.

## Conceitos — para entender

| Arquivo | Do que trata |
|---|---|
| [concepts/calendario-transicao.md](concepts/calendario-transicao.md) | O que vigora em cada ano de 2026 a 2033 |
| [concepts/simples-na-reforma.md](concepts/simples-na-reforma.md) | Simples "por dentro" × regime regular de IBS/CBS e o efeito no crédito do cliente |

## Receitas — para fazer

| Arquivo | Resolve |
|---|---|
| [patterns/avaliar-opcao-regime-regular-simples.md](patterns/avaliar-opcao-regime-regular-simples.md) | Decidir se o optante do Simples deve recolher IBS/CBS pelo regime regular |

## Consulta rápida

- [quick-reference.md](quick-reference.md) — calendário, prazos de opção e erros comuns

## O que este domínio NÃO cobre

- Alíquotas de referência definitivas de CBS/IBS (fixadas por resolução do Senado e ajustadas até 2033).
- Regimes específicos e diferenciados (reduções de 30%/60%, cesta básica, saúde, educação, imobiliário, combustíveis).
- Split payment, cashback e a operação do Comitê Gestor do IBS.
- Imposto Seletivo por produto.

---

> **Responsabilidade:** conteúdo montado a partir de fontes secundárias (serasaexperian.com.br, e-auditoria.com.br, escolasuperioresn.com.br, cgmlaw.com.br, pfpadvogados.com.br) consultadas em 2026-09-24; **o texto da LC 214/2025 não foi conferido na fonte primária** (Planalto indisponível na consulta). A regulamentação ainda está em evolução — revise a cada exercício.
