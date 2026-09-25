# Conciliar PGDAS-D, folha e contabilidade por competência

> **Resolve:** confirmar que receita, DAS, INSS, FGTS e proventos batem entre as fontes de uma competência, apontando divergências acima da tolerância antes da homologação.
> **Fonte:** conciliação manual das amostras de ago/2026 feita em 2026-09-24 (as 6 regras fecharam com diferença zero); DEFINE e DESIGN do ciclo 1 (tolerância padrão R$ 1,00, regras R1–R6). Válida para optantes do Simples; outros regimes exigem regras adicionais.

## Quando usar

- Depois da extração e das validações internas de todos os documentos de uma competência.
- Após cada ajuste manual (a conciliação é refeita).

## Quando NÃO usar

- Documento com validação interna falhando → corrija ou ajuste primeiro; conciliar números que não fecham internamente gera falsa divergência.
- Competência sem uma das fontes → registre `missing_source` (alerta), não divergência.

## Passo a passo

1. **Confirme o mapeamento de contas** da empresa: vendas (balancete e DRE), despesa de Simples, Simples a Recolher, INSS a Pagar, FGTS a Pagar, Salários a Pagar. Sem mapeamento → pendência de cadastro.
2. **R1 Receita:** PGDAS RPA × DRE conta de vendas × balancete (crédito − débito da conta de vendas no período). As devoluções entram como débito.
3. **R2 DAS:** PGDAS total do débito declarado (2.8) × DRE despesa "Simples Nacional" × balancete débito da conta de despesa no período.
4. **R3 INSS:** folha "INSS Folha"/GPS empregados × balancete crédito em INSS a Pagar.
5. **R4 FGTS:** folha "Total FGTS apurado" × balancete crédito em FGTS a Pagar (e débito na despesa de FGTS).
6. **R5 Proventos:** folha TOTAL DE ADICIONAIS × balancete crédito em Salários a Pagar.
7. **R6 DAS anterior:** PGDAS da competência anterior (total) × balancete desta competência (saldo anterior de Simples a Recolher). Confirma que o DAS provisionado no mês anterior é o declarado.
8. **Compare com a tolerância** (padrão R$ 1,00, configurável por escritório): `|A − B| ≤ tolerância` → `ok`; senão → `divergent`.
9. **Para cada divergência,** o analista corrige o valor (ajuste com motivo) ou justifica (texto + autor + data). Sem isso, a homologação fica bloqueada.
10. **Registre** regra, competência, valores, diferença, status e justificativa.

## Exemplo (valores da amostra, ago/2026)

| Regra | Lado A | Lado B | Diferença |
|---|---|---|---|
| R1 | 203.180,77 | 205.577,54 − 2.396,77 = 203.180,77 | 0,00 |
| R2 | 23.430,47 | 23.430,47 | 0,00 |
| R3 | 2.963,53 | 2.963,53 | 0,00 |
| R4 | 2.706,49 | 2.706,49 | 0,00 |
| R5 | 34.212,13 | 34.212,13 | 0,00 |
| R6 | 38.975,46 (PGDAS jul) | 38.975,46 | 0,00 |

## Como saber que deu certo

- Cada regra tem status por competência; nenhuma `divergent` fica sem correção ou justificativa.
- A tela mostra os dois lados com o documento e a página de origem.

## Quando dá errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| R1 diverge pelo valor das devoluções | Usou o crédito bruto de vendas | Use crédito − débito |
| R1 diverge em empresa com regime de caixa | PGDAS por caixa × contabilidade por competência | Registre justificativa; conciliar por caixa exige outra regra |
| R2 diverge pela diferença de um mês | DAS lançado na competência do pagamento | Verifique R6 e o critério de provisão do escritório |
| R3 diverge | Inclui INSS de sócios ou autônomos num lado só | Compare bases iguais (empregados × empregados) |
| Todas as regras `missing_source` | Mapeamento de contas ausente | Cadastre o mapeamento (passo 1) |

## Relacionados

- [../concepts/pgdas-d-estrutura.md](../concepts/pgdas-d-estrutura.md)
- [../concepts/relatorios-alterdata.md](../concepts/relatorios-alterdata.md)
- [../../simples-nacional/patterns/calcular-das-mensal.md](../../simples-nacional/patterns/calcular-das-mensal.md)
