# Encontrar o ponto de virada entre regimes

> **Resolve:** descobrir o valor de uma variável (margem, folha/receita, receita, créditos) em que o regime recomendado deixa de ser o mais barato — exigência do PRD (§9) para toda recomendação.
> **Fonte:** PRD do projeto (§9, variáveis mínimas de sensibilidade); método numérico de uso geral; exemplo fictício calculado em 2026-09-24.

## Quando usar

- Depois de rodar o comparativo base ([comparar-regimes-exercicio.md](comparar-regimes-exercicio.md)).
- Quando a diferença entre os dois melhores regimes é pequena.
- Para explicar ao cliente "até onde" a recomendação vale.

## Quando NÃO usar

- Quando a variável altera a elegibilidade (ex.: receita que cruza o teto do Simples) — aí o ponto de virada é **jurídico** e deve ser reportado como limite de elegibilidade, não como equilíbrio de custo.

## Passo a passo

1. **Escolha uma variável por vez**, entre as mínimas do PRD: receita, margem bruta, folha/pró-labore, relação folha/receita, despesas dedutíveis, créditos sobre insumos, mix de atividades, B2B/B2C, ICMS/ISS, benefícios.
2. **Fixe todas as outras** no cenário base.
3. **Defina o intervalo plausível** (ex.: margem líquida de 0% a 40%; folha/receita de 10% a 45%).
4. **Calcule o custo total dos regimes elegíveis** em pontos do intervalo (passo de 1 p.p. basta para o relatório).
5. **Localize a troca de ordem** entre o primeiro e o segundo colocados; refine por bisseção até a precisão desejada (ex.: 0,1 p.p. ou R$ 1.000).
6. **Verifique descontinuidades:** mudança de faixa do Simples, Fator R em 28%, adicional de IRPJ, LC 224 acima de R$ 5 mi, sublimite. O ponto de virada pode ser um salto, não um cruzamento suave.
7. **Registre:** variável, valor no cenário base, ponto de virada, distância percentual até ele e qual regime passa a vencer.
8. **Classifique a robustez:** distância > 20% → robusta; 5–20% → atenção; < 5% → frágil (e candidata a "inconclusivo"). Faixas sugeridas — **política a configurar pelo escritório**.

## Exemplo (fictício): Presumido × Real em serviços

Receita anual R$ 3 mi, abaixo de R$ 5 mi (sem LC 224), folha igual nos dois regimes (encargos iguais), PIS/Cofins do Real sem créditos relevantes.
- Presumido: base 3 mi × 32% = 960 mil → IRPJ 144,0 mil + adicional 10% × (960 − 240) = 72,0 mil + CSLL 9% = 86,4 mil → **R$ 302,4 mil**; PIS/Cofins 3,65% = R$ 109,5 mil → total **R$ 411,9 mil**.
- Real: PIS/Cofins 9,25% = R$ 277,5 mil; IRPJ + adicional + CSLL sobre o lucro L (L > R$ 240 mil) = 0,34 × L − 24 mil.
- Igualando: 411,9 = 277,5 + 0,34 × L − 24 → L ≈ R$ 466 mil → **margem tributável ≈ 15,5%**.
- Leitura: com margem tributável abaixo de ~15,5% o Real vence; acima, o Presumido. Se o cliente opera com 25%, a recomendação pelo Presumido é robusta (distância > 20%).

(Simplificação para ilustrar o método: sem créditos de PIS/Cofins no Real e sem adições/exclusões; o motor calcula exato.)

## Como saber que deu certo

- Para cada variável testada há um valor de virada ou a indicação "sem virada no intervalo".
- O relatório mostra a distância do cenário base até a virada.
- Pontos de salto (faixa, Fator R, limites) aparecem identificados como tais.

## Quando dá errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Virada "some" ao refinar | Descontinuidade de faixa | Reporte como salto (passo 6) |
| Várias viradas na mesma variável | Faixas do Simples alternando | Reporte todas, em ordem |
| Virada fora do plausível | Intervalo mal escolhido | Revise o passo 3 com o histórico do cliente |
| Regime inelegível aparece vencendo | Elegibilidade não reavaliada no ponto | Reteste a elegibilidade em cada ponto |

## Relacionados

- [comparar-regimes-exercicio.md](comparar-regimes-exercicio.md)
- [../../lucro-presumido/concepts/base-presumida-e-lc224.md](../../lucro-presumido/concepts/base-presumida-e-lc224.md)
