# Comparar os três regimes para um exercício

> **Resolve:** produzir o quadro comparativo anual e mensal de Simples, Presumido e Real, com recomendação explicável, riscos, premissas e pendências.
> **Fonte:** PRD do projeto (§5, §9, §10), domínios `simples-nacional`, `lucro-presumido` e `lucro-real` desta base; heurísticas de prática de mercado marcadas como tais.

## Quando usar

- Planejamento anual (idealmente em novembro/dezembro, antes das opções de janeiro).
- Mudança relevante no cliente: crescimento, nova atividade, entrada de sócio, mudança na folha.

## Quando NÃO usar

- Dados não homologados ou conciliação divergente sem justificativa → a recomendação fica bloqueada (PRD §10.2); no máximo uma prévia marcada como incompleta.
- Pedido de "reduzir o imposto" alterando fatos → fora do escopo ([../concepts/elisao-x-evasao.md](../concepts/elisao-x-evasao.md)).

## Passo a passo

1. **Parta do dossiê homologado** (snapshot com hash): receitas por atividade e mês, folha e pró-labore, DRE e balancete, DAS pago.
2. **Defina o ano projetado e o método de projeção** (realizado, média, sazonalidade ≥ 24 meses ou orçamento) e registre como premissa.
3. **Monte três cenários** (conservador, base, expansão) variando explicitamente receita, margem e folha.
4. **Rode a elegibilidade** dos três regimes no ano projetado ([../concepts/elegibilidade-antes-do-custo.md](../concepts/elegibilidade-antes-do-custo.md)). Os inelegíveis saem do ranking, com o motivo.
5. **Calcule o Simples** mês a mês ([../../simples-nacional/patterns/calcular-das-mensal.md](../../simples-nacional/patterns/calcular-das-mensal.md)) com RBT12 móvel e Fator R mensal; some a CPP do Anexo IV e o ICMS/ISS fora do DAS, se houver sublimite.
6. **Calcule o Presumido** por trimestre ([../../lucro-presumido/patterns/calcular-trimestre-presumido.md](../../lucro-presumido/patterns/calcular-trimestre-presumido.md)), com a LC 224 se a receita passar de R$ 5 mi; PIS/Cofins mensais.
7. **Calcule o Real** ([../../lucro-real/patterns/apurar-irpj-csll-lucro-real.md](../../lucro-real/patterns/apurar-irpj-csll-lucro-real.md)) com os ajustes listados e PIS/Cofins com créditos estimados por natureza de conta; escolha a forma de apuração que minimiza o custo.
8. **Some os encargos de folha** de cada regime ([../concepts/encargos-folha-por-regime.md](../concepts/encargos-folha-por-regime.md)) e o ICMS/ISS/IPI calculados de forma equivalente nos regimes fora do Simples.
9. **Monte as métricas por regime:** tributos por espécie, mês e ano; alíquota efetiva total; carga sobre consumo, renda e folha; créditos e retenções (separados); resultado líquido e caixa após tributos; custo de conformidade (separado); confiança dos dados; risco.
10. **Aplique a regra de decisão:** entre os elegíveis, menor custo tributário total. Se a diferença para o segundo for menor que o limiar configurado → "resultado inconclusivo". Dados críticos ausentes → bloquear.
11. **Rode a sensibilidade** ([encontrar-ponto-de-virada.md](encontrar-ponto-de-virada.md)) nas variáveis mínimas do PRD e registre os pontos de virada.
12. **Considere o efeito no cliente B2B:** se os clientes aproveitam crédito, registre o impacto comercial do Simples (crédito menor) como fator qualitativo.
13. **Redija a explicação:** "Recomendamos X porque…", três fatores econômicos principais, condições jurídicas, economia estimada (absoluta e %), intervalo de sensibilidade, riscos, premissas, dados ausentes, data-base normativa.
14. **Envie para revisão:** o responsável técnico aprova ou devolve; só então o relatório é emitido.

## Como saber que deu certo

- Cada número do quadro tem fórmula, base, alíquota, competência, regra e origem (drill-down).
- Nenhum regime inelegível aparece como recomendado.
- A mesma entrada com a mesma versão de regras produz o mesmo resultado.
- A recomendação traz o ponto de virada e o responsável que aprovou.

## Quando dá errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Simples muito barato perto do teto | Exclusão no ano projetado não testada | Refaça o passo 4 com a projeção mensal |
| Presumido vence com folga em serviço de margem baixa | LC 224 ou encargos de folha omitidos | Refaça os passos 6 e 8 |
| Real perde sempre | PIS/Cofins sem créditos ou prejuízo não compensado | Estime os créditos; inclua o saldo de prejuízo com trava |
| Recomendação muda com pequena variação | Resultado perto do limiar | Declare inconclusivo e mostre a sensibilidade |
| Economia "boa demais" | Premissa sem suporte (ex.: folha que não existe) | Exija justificativa e documento para a premissa |

## Relacionados

- [../quick-reference.md](../quick-reference.md)
- [encontrar-ponto-de-virada.md](encontrar-ponto-de-virada.md)
- [../../reforma-tributaria/patterns/avaliar-opcao-regime-regular-simples.md](../../reforma-tributaria/patterns/avaliar-opcao-regime-regular-simples.md)
