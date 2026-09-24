# Calendário de transição 2026–2033

> **O que é:** a sequência anual em que CBS, IBS e o Imposto Seletivo entram e PIS, Cofins, IPI, ICMS e ISS saem, que define quais tributos o motor deve calcular em cada exercício projetado.
> **Fonte:** EC 132/2023 e LC 214/2025, via serasaexperian.com.br e qive.com.br (consultados em 2026-09-24). **LC 214 não conferida na fonte primária.** A calibragem das alíquotas de referência depende de resolução do Senado — os percentuais "plenos" não estão definidos aqui.

## Por que isto existe

O PRD exige que o comparativo diga se o cálculo é histórico, corrente ou projetado e quais regras valiam na versão usada. Um planejamento feito em 2026 para 2027 já atravessa a maior virada do sistema: PIS/Cofins deixam de existir.

## Como funciona

**2026 — ano de teste.** CBS 0,9% e IBS 0,1% destacados nos documentos fiscais, compensáveis com PIS/Cofins; dispensa de recolhimento para quem cumpre as obrigações acessórias. Na prática, o custo continua sendo o de PIS/Cofins/ICMS/ISS. O Simples fica fora do teste.

**2027 — virada federal.** PIS e Cofins extintos; CBS plena (não cumulativa, crédito financeiro amplo); IPI zerado, exceto para produtos com incentivo da Zona Franca de Manaus; Imposto Seletivo começa (produtos prejudiciais à saúde/ambiente); IBS a 0,1% (0,05% estadual + 0,05% municipal). O Simples passa a ter IBS/CBS no DAS, com a opção pelo regime regular. Fontes indicam redução de 0,1 p.p. na CBS em 2027–2028 para compensar o IBS — **não verificado**.

**2028.** Igual a 2027.

**2029–2032 — troca estadual e municipal.** ICMS e ISS caem para 90%, 80%, 70% e 60% das alíquotas; o IBS cresce na mesma proporção. Os dois sistemas convivem: o motor precisa calcular ICMS/ISS reduzidos **e** IBS no mesmo exercício.

**2033 — regime pleno.** ICMS e ISS extintos; CBS + IBS + IS.

**Mudança de lógica que afeta o planejamento:**
- Crédito **financeiro**: tudo que foi pago na aquisição e destacado gera crédito (salvo uso e consumo pessoal e exceções), em vez da lista restrita de insumos do PIS/Cofins atual.
- A diferença cumulativo × não cumulativo (Presumido × Real) deixa de existir para os tributos sobre consumo: fora do Simples, todos pagam CBS/IBS não cumulativos. A escolha Presumido × Real passa a depender só de IRPJ/CSLL (e da folha, que é igual).
- O crédito que o cliente B2B obtém depende do regime do fornecedor: integral do regime regular; limitado ao valor recolhido no DAS quando o fornecedor é do Simples "por dentro".

## O que costuma ser confundido

| Isto | Não é isto |
|---|---|
| 2026 é teste, com custo zero para quem cumpre as obrigações | 2026 já soma 1% de carga |
| PIS/Cofins acabam em 2027 | Acabam em 2033 |
| ICMS/ISS acabam em 2033, reduzindo desde 2029 | Acabam em 2027 |
| IPI zerado, exceto ZFM | IPI extinto para tudo |
| Presumido × Real continua decidindo PIS/Cofins em 2027 | Continua existindo cumulativo |

## Quando isto importa na prática

- **Motor:** módulos CBS, IBS e IS parametrizados por exercício, com versão normativa; ICMS/ISS com fator de redução em 2029–2032.
- **Comparativo 2027+:** a vantagem do cumulativo (serviços no Presumido) desaparece. Serviços com pouca compra passam a pagar CBS "cheia" sobre o valor agregado — o ganho relativo do Simples para prestadores B2C pode aumentar.
- **B2B:** fornecedores do Simples podem perder competitividade se o cliente aproveita crédito; ver `simples-na-reforma.md`.

## Relacionados

- [simples-na-reforma.md](simples-na-reforma.md)
- [../../lucro-presumido/concepts/pis-cofins-cumulativo.md](../../lucro-presumido/concepts/pis-cofins-cumulativo.md)
- [../../lucro-real/concepts/pis-cofins-nao-cumulativo.md](../../lucro-real/concepts/pis-cofins-nao-cumulativo.md)
