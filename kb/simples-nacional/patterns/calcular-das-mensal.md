# Calcular o DAS de uma competência

> **Resolve:** chegar ao valor do DAS de um mês (real ou projetado), por atividade, com memória de cálculo auditável.
> **Fonte:** LC 123/2006, art. 18 e Anexos; procedimento validado ao recompor o PGDAS-D de jun/2026 da amostra do projeto (diferença zero).

## Quando usar

- Simular o Simples mês a mês no ano projetado.
- Conferir um PGDAS-D importado (a soma recalculada deve bater com o DAS declarado).
- Explicar ao cliente de onde vem o valor do DAS.

## Quando NÃO usar

- A empresa é inelegível no período → não calcule; marque "não aplicável" (ver [testar-elegibilidade-simples.md](testar-elegibilidade-simples.md)).
- MEI → valores fixos, fora deste domínio.

## Passo a passo

1. **Monte a série de receitas** mensais do mercado interno e externo, no mínimo dos 12 meses anteriores à competência (no PGDAS-D: seção 2.2).
2. **Calcule o RBT12** = soma dos 12 meses anteriores ao PA (não incluir o mês). Em início de atividade, use o RBT12 proporcionalizado.
3. **Segregue a receita do mês por atividade**: anexo, com ou sem ST, monofásico, exportação, ISS retido. Cada linha vira um cálculo.
4. **Defina o anexo de cada linha**; para atividades do § 5º-I, calcule o Fator R com a folha dos 12 meses anteriores e escolha III (r ≥ 28%) ou V.
5. **Ache a faixa** pelo RBT12 na tabela do anexo ([../quick-reference.md](../quick-reference.md)).
6. **Calcule a efetiva:** `(RBT12 × nominal − parcela) ÷ RBT12`. Guarde com pelo menos 6 casas decimais na memória.
7. **Reparta** a efetiva pelos percentuais da faixa e **zere** os tributos que não se aplicam à linha (ICMS se ST; PIS/Cofins se monofásico; PIS/Cofins/ICMS/ISS/IPI se exportação; ISS se retido).
8. **Caso faixa 6 com ICMS/ISS ainda no DAS:** calcule o ICMS/ISS com a efetiva da faixa 5 × percentual de ICMS/ISS da faixa 5 (ver conceito).
9. **Multiplique** cada percentual pela receita da linha; arredonde cada tributo em centavos.
10. **Some** por tributo e no total. Esse é o DAS da competência.
11. **Anexo IV:** calcule à parte a CPP (20% + RAT sobre a folha do mês) — ela não está no DAS, mas é custo do regime.
12. **Registre a memória:** RBT12, faixa, nominal, parcela, efetiva, repartição, receita por linha e resultado por tributo.

## Exemplo (fictício)

Comércio, RBT12 R$ 1.000.000, receita do mês R$ 90.000 sem ST:
- Faixa 4 do Anexo I: nominal 10,70%, parcela R$ 22.500.
- Efetiva: (1.000.000 × 10,7% − 22.500) ÷ 1.000.000 = **8,45%**.
- DAS: 90.000 × 8,45% = **R$ 7.605,00**, repartido pelos percentuais da faixa 4.

## Como saber que deu certo

- Na conferência de um PGDAS-D real: o total por atividade e o total geral batem com o documento, com diferença de no máximo R$ 0,01 por tributo (arredondamento).
- Na simulação: a soma dos tributos por linha é igual à efetiva × receita (± centavos).

## Quando dá errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| DAS calculado maior que o declarado | Usou alíquota nominal ou esqueceu a parcela a deduzir | Refaça o passo 6 |
| Diferença exatamente na parcela de ICMS | Receita com ST não segregada | Separe a linha com ST e zere o ICMS |
| Faixa diferente da do PGDAS-D | RBT12 incluiu o mês corrente ou omitiu mercado externo | Refaça o passo 2 |
| ICMS diferente na faixa 6 | Usou a repartição da faixa 6 para o ICMS | Use a faixa 5 para o ICMS (passo 8) |
| Diferença de centavos em vários tributos | Arredondou a efetiva antes de multiplicar | Arredonde só o valor de cada tributo |

## Relacionados

- [../concepts/aliquota-efetiva-e-reparticao.md](../concepts/aliquota-efetiva-e-reparticao.md)
- [../concepts/fator-r-e-anexos.md](../concepts/fator-r-e-anexos.md)
- [../../documentos-fonte/patterns/conciliar-fontes-por-competencia.md](../../documentos-fonte/patterns/conciliar-fontes-por-competencia.md)
