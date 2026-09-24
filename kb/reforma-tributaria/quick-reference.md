# Reforma tributária — consulta rápida

> Para quem já entende o domínio e só precisa lembrar. Fontes: EC 132/2023, LC 214/2025, lidas via fontes secundárias em 2026-09-24 — conferir na lei antes de parametrizar.

## Calendário

| Ano | CBS | IBS | PIS/Cofins | IPI | ICMS/ISS | IS |
|---|---|---|---|---|---|---|
| 2026 | 0,9% (teste) | 0,1% (teste) | Vigentes | Vigente | 100% | — |
| 2027 | Plena | 0,1% (0,05% UF + 0,05% mun.) | **Extintos** | Zero (exceto ZFM) | 100% | Início |
| 2028 | Plena | 0,1% | — | Zero (exceto ZFM) | 100% | Vigente |
| 2029 | Plena | Crescente | — | Zero (exceto ZFM) | 90% | Vigente |
| 2030 | Plena | Crescente | — | Zero (exceto ZFM) | 80% | Vigente |
| 2031 | Plena | Crescente | — | Zero (exceto ZFM) | 70% | Vigente |
| 2032 | Plena | Crescente | — | Zero (exceto ZFM) | 60% | Vigente |
| 2033 | Plena | Pleno | — | Zero (exceto ZFM) | **Extintos** | Vigente |

2026: dispensa de recolhimento para quem cumpre as obrigações acessórias (destaque em documento fiscal). Simples não participa do teste de 2026.

## Decisão rápida

| Se você quer... | Faça |
|---|---|
| Saber se o optante do Simples deve ir para o regime regular de IBS/CBS | [patterns/avaliar-opcao-regime-regular-simples.md](patterns/avaliar-opcao-regime-regular-simples.md) |
| Projetar 2027 no Presumido/Real | Trocar PIS/Cofins por CBS não cumulativa (crédito amplo) |
| Projetar 2026 | Ainda PIS/Cofins; CBS/IBS de teste sem custo para quem cumpre as obrigações |

## Prazos de opção do Simples (regime regular de IBS/CBS)

| Opção feita em | Vale para | Observação |
|---|---|---|
| Setembro de 2026 | 1º semestre de 2027 | Primeira janela — fontes citam prazo até 30/09/2026 |
| Março (seguinte) | 2º semestre do ano | Conforme fontes; conferir a regulamentação do CGSN |
| Setembro | 1º semestre do ano seguinte | Opção semestral |

## Erros comuns

| ❌ Não faça | ✅ Faça |
|---|---|
| Projetar 2027+ com PIS/Cofins | Usar CBS (e IBS em transição) |
| Supor neutralidade do Simples para clientes B2B | Avaliar o crédito que o cliente perde (PRD §8.5) |
| Tratar alíquotas de referência como fixas | Parametrizar por exercício, com versão |
| Esquecer que ICMS/ISS convivem com IBS até 2032 | Calcular os dois sistemas proporcionalmente |
| Perder a janela de setembro | Avaliar a opção antes do prazo |

## Onde procurar o resto

| Assunto | Arquivo |
|---|---|
| Começar do zero | [index.md](index.md) |
| Simples hoje | [../simples-nacional/index.md](../simples-nacional/index.md) |
