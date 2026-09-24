# Calcular um trimestre no Lucro Presumido

> **Resolve:** chegar a IRPJ, adicional, CSLL, PIS e Cofins de um trimestre, com memória, para simulação ou conferência.
> **Fonte:** Lei 9.249/1995, Lei 9.430/1996, Lei 9.718/1998, LC 224/2025; exemplo numérico fictício calculado em 2026-09-24.

## Quando usar

- Simular o Presumido para o ano projetado (4 trimestres; PIS/Cofins mensais somados).
- Conferir a apuração de um cliente já no Presumido.

## Quando NÃO usar

- Empresa obrigada ao Lucro Real ou com receita do ano anterior acima de R$ 78 mi → Presumido inelegível; registre o motivo.
- Atividades com regras próprias (imobiliária com permuta, factoring, instituições financeiras) → tratamento específico, fora deste domínio.

## Passo a passo

1. **Confirme a elegibilidade:** receita total do ano anterior ≤ R$ 78 mi (proporcional se iniciou no ano) e nenhuma hipótese do art. 14 da Lei 9.718/1998.
2. **Segregue a receita bruta do trimestre por atividade** (revenda, indústria, serviços, transporte), já deduzidas as devoluções, as vendas canceladas e os descontos incondicionais.
3. **Aplique a presunção** de IRPJ e de CSLL de cada atividade ([../quick-reference.md](../quick-reference.md)).
4. **Aplique a LC 224/2025** se a receita acumulada do ano passar de R$ 5 mi: multiplique por 1,10 o percentual da parcela excedente (IRPJ desde jan/2026; CSLL desde abr/2026). Se o cliente tiver liminar, simule os dois cenários e registre a premissa.
5. **Some integralmente** as demais receitas do trimestre: rendimentos financeiros, ganhos de capital, juros recebidos, outras receitas.
6. **IRPJ** = 15% × base; **adicional** = 10% × (base − R$ 60.000), se positivo. Em trimestre com menos de 3 meses de atividade, o limite é R$ 20.000 × meses.
7. **CSLL** = 9% × base de CSLL.
8. **Deduza as retenções** do trimestre (IRRF 1,5% e CSLL retida sobre serviços, IRRF de aplicações) — no comparativo, mantenha-as separadas do custo econômico.
9. **PIS** = 0,65% e **Cofins** = 3% sobre a receita bruta de cada mês (excluindo ICMS destacado, receitas monofásicas com alíquota zero e exportação).
10. **Registre a memória:** receita por atividade, percentuais, base, excedentes, alíquotas, retenções e resultado.

## Exemplo (fictício)

Comércio, receita no trimestre R$ 900.000 (sem ST, sem monofásico), sem outras receitas, abaixo de R$ 5 mi/ano:

| Item | Cálculo | Valor (R$) |
|---|---|---|
| Base IRPJ | 900.000 × 8% | 72.000,00 |
| IRPJ | 72.000 × 15% | 10.800,00 |
| Adicional | (72.000 − 60.000) × 10% | 1.200,00 |
| Base CSLL | 900.000 × 12% | 108.000,00 |
| CSLL | 108.000 × 9% | 9.720,00 |
| PIS | 900.000 × 0,65% | 5.850,00 |
| Cofins | 900.000 × 3% | 27.000,00 |
| **Total federal** | | **54.570,00 (6,06% da receita)** |

ICMS, folha e demais tributos ficam de fora e são somados no comparativo.

## Como saber que deu certo

- Na conferência: IRPJ e CSLL batem com o DARF/DCTF do trimestre, e PIS/Cofins com a EFD-Contribuições.
- Na simulação: a carga federal sobre a receita fica coerente com a presunção (comércio ~6%, serviços ~11–16% sem LC 224, antes de encargos).

## Quando dá errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| IRPJ muito alto em serviço misto | Aplicou 32% à receita de revenda | Refaça o passo 2 |
| Adicional diferente do DARF | Limite mensal (R$ 20 mil) em vez de trimestral | Use R$ 60 mil por trimestre |
| Base menor que a declarada | Faltaram receitas financeiras | Refaça o passo 5 |
| CSLL do 1º tri/2026 majorada | LC 224 aplicada à CSLL antes de abril | CSLL majorada só a partir de 01/04/2026 |
| Custo total inflado | Retenções somadas como custo | Trate retenção como antecipação |

## Relacionados

- [../concepts/base-presumida-e-lc224.md](../concepts/base-presumida-e-lc224.md)
- [../concepts/pis-cofins-cumulativo.md](../concepts/pis-cofins-cumulativo.md)
- [../../planejamento-comparativo/patterns/comparar-regimes-exercicio.md](../../planejamento-comparativo/patterns/comparar-regimes-exercicio.md)
