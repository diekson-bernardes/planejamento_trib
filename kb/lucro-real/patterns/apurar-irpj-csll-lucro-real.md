# Apurar IRPJ e CSLL no Lucro Real a partir do balancete

> **Resolve:** calcular IRPJ, adicional e CSLL de um período (trimestre ou ano) partindo do resultado contábil conciliado, com cada ajuste rastreável.
> **Fonte:** Decreto 9.580/2018 (RIR), Leis 8.981/1995 e 9.065/1995 (trava de 30%); exemplo fictício calculado em 2026-09-24.

## Quando usar

- Simular o Real no comparativo.
- Montar a ponte contábil-fiscal no motor (PRD §8.4).

## Quando NÃO usar

- Balancete que não fecha (débito ≠ crédito) ou DRE sem conciliação com o PGDAS/folha → primeiro resolva a qualidade dos dados ([../../documentos-fonte/patterns/conciliar-fontes-por-competencia.md](../../documentos-fonte/patterns/conciliar-fontes-por-competencia.md)).
- Instituições financeiras e atividades com regras próprias.

## Passo a passo

1. **Escolha a forma de apuração** (trimestral ou anual) e o período.
2. **Parta do lucro antes do IRPJ e da CSLL** na DRE conciliada. Se o IRPJ/CSLL do período já estiverem lançados como despesa, some-os de volta.
3. **Liste as adições** conta a conta: multas punitivas, brindes, doações indedutíveis, provisões não dedutíveis, equivalência negativa. Cada adição com conta, valor, competência e justificativa.
4. **Liste as exclusões:** dividendos recebidos, equivalência positiva, reversões de provisões adicionadas antes, incentivos admitidos. Idem: conta, valor, justificativa.
5. **Calcule o lucro ajustado** = lucro contábil + adições − exclusões.
6. **Compense o prejuízo fiscal:** mínimo entre o saldo de prejuízo e 30% do lucro ajustado (se positivo). Atualize o saldo da parte B.
7. **IRPJ** = 15% × lucro real; **adicional** = 10% × (lucro real − R$ 20.000 × meses do período).
8. **Deduza** do IRPJ os incentivos dedutíveis do imposto (PAT, doações incentivadas etc., dentro dos limites) e as retenções e estimativas pagas.
9. **CSLL:** repita os passos 3 a 6 com os ajustes do e-Lacs e a base negativa própria; aplique 9%.
10. **Se o resultado ajustado for negativo:** IRPJ e CSLL zero; o valor vira prejuízo fiscal ou base negativa a compensar no futuro (com trava).
11. **Registre a memória:** lucro contábil, cada ajuste, lucro ajustado, compensação, bases, alíquotas e saldos finais de prejuízo.

## Exemplo (fictício, trimestral)

| Item | Valor (R$) |
|---|---|
| Lucro contábil antes de IRPJ/CSLL | 200.000 |
| (+) Multa de trânsito (punitiva) | 3.000 |
| (+) Provisão para contingência trabalhista | 17.000 |
| (−) Dividendos recebidos | 10.000 |
| = Lucro ajustado | 210.000 |
| (−) Compensação: saldo 150.000; limite 30% = 63.000 | 63.000 |
| = Lucro real | 147.000 |
| IRPJ 15% | 22.050 |
| Adicional 10% × (147.000 − 60.000) | 8.700 |
| CSLL 9% (supondo a mesma base) | 13.230 |
| **Total IRPJ + CSLL** | **43.980** |
| Saldo de prejuízo para o próximo período | 87.000 |

## Como saber que deu certo

- Todo ajuste tem conta de origem no balancete e justificativa.
- Lucro contábil + adições − exclusões − compensação = lucro real, sem diferença.
- O saldo de prejuízo final = saldo inicial − compensado + prejuízo gerado.

## Quando dá errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Imposto muito baixo com prejuízo acumulado | Compensou 100% | Limite a 30% (passo 6) |
| IRPJ incide sobre CSLL já deduzida | Deduziu a CSLL da base do IRPJ | A CSLL é adição na base do IRPJ |
| Lucro contábil diferente da DRE | IRPJ/CSLL já lançados como despesa | Some-os de volta (passo 2) |
| Ajuste sem conta de origem | Ajuste manual sem suporte | Bloqueie até ter conta e justificativa |

## Relacionados

- [../concepts/lucro-contabil-ao-tributavel.md](../concepts/lucro-contabil-ao-tributavel.md)
- [../concepts/obrigatoriedade.md](../concepts/obrigatoriedade.md)
- [../concepts/pis-cofins-nao-cumulativo.md](../concepts/pis-cofins-nao-cumulativo.md)
