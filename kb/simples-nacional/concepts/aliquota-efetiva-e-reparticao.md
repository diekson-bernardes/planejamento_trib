# Alíquota efetiva e repartição do DAS

> **O que é:** a alíquota que efetivamente incide sobre a receita do mês no Simples, derivada da nominal da faixa menos uma parcela a deduzir, e dividida entre os tributos do DAS por percentuais fixos de cada faixa.
> **Fonte:** LC 123/2006, art. 18 e Anexos I–V (redação LC 155/2016); verificação numérica feita com o PGDAS-D de jun/2026 da amostra do projeto (cálculo reproduzido ao centavo em 2026-09-24).

## Por que isto existe

Desde 2018 o Simples é progressivo "por dentro": cada faixa tem uma alíquota nominal, mas uma parcela a deduzir suaviza o salto entre faixas. Quem simula com a nominal superestima o imposto — em alguns casos em mais de 50%.

## Como funciona

1. **RBT12** é a receita bruta dos 12 meses **anteriores** ao período de apuração (PA). A receita do próprio mês não entra.
2. RBT12 define a faixa do anexo da atividade. A fórmula é:
   `efetiva = (RBT12 × nominal − parcela a deduzir) ÷ RBT12`.
3. A efetiva é aplicada sobre a **receita do mês de cada atividade** (segregada: revenda, industrialização, serviço, com ou sem ST/monofásico, exportação).
4. O valor resultante é **repartido** entre IRPJ, CSLL, Cofins, PIS, CPP, IPI, ICMS e ISS pelos percentuais da faixa. A repartição importa porque:
   - receitas com ICMS-ST ou PIS/Cofins monofásico **retiram** a parcela do tributo já recolhido;
   - exportação retira PIS, Cofins, ICMS/ISS (e IPI);
   - quando ICMS/ISS saem do DAS (sublimite), a parcela correspondente deixa de ser cobrada no DAS.

## O caso da faixa 6 (observado na amostra)

Na faixa 6 (RBT12 acima de R$ 3,6 mi) a repartição não tem parcela de ICMS/ISS — acima do sublimite esses tributos, em regra, são recolhidos fora. Mas pode acontecer de o RBT12 estar na faixa 6 enquanto o sublimite **ainda não produz efeito** (ele é aferido pela receita do ano-calendário, não pelo RBT12). Nesse caso a amostra mostra:

| Parte | Como foi calculada | Conferência na amostra |
|---|---|---|
| Federal (IRPJ, CSLL, Cofins, PIS, CPP) | Efetiva da faixa 6 × repartição da faixa 6 | RBT12 3.841.113,82 → efetiva 9,159% → bateu nas duas atividades |
| ICMS no DAS | Efetiva **da faixa 5** × 33,5% (parcela de ICMS da faixa 5) | 12,027% × 33,5% = 4,029% → R$ 7.410,40 sobre R$ 183.921,20 ✓ |
| ICMS na receita com ST | Zero (retirado) | 0,00 ✓ |

O dispositivo exato que determina usar a faixa 5 para o ICMS/ISS não foi conferido na norma (provável LC 123, art. 18, § 17, ou a Resolução CGSN nº 140/2018) — **não verificado na fonte primária**; a regra acima foi deduzida do documento oficial gerado pelo PGDAS-D.

## O que costuma ser confundido

| Isto | Não é isto |
|---|---|
| RBT12 = 12 meses anteriores ao PA | Receita dos últimos 12 meses incluindo o mês |
| Faixa é definida pelo RBT12 | Faixa definida pela receita do ano (RBA) |
| Sublimite produz efeito pela receita do ano-calendário | Sublimite testado pelo RBT12 |
| Efetiva varia mês a mês | Alíquota fixa do ano |
| Repartição muda por faixa | Percentual fixo de cada tributo em todo o anexo |

## Quando isto importa na prática

- No **motor tributário**: cada mês projetado precisa recalcular o RBT12 móvel — um mês forte empurra os 12 seguintes para outra faixa.
- Na **conciliação**: o total do DAS deve igualar a soma dos tributos por atividade (validação interna do PGDAS-D).
- No **comparativo**: a carga do Simples cresce de forma não linear perto das mudanças de faixa; o ponto de virada contra o Presumido costuma aparecer aí.
- Para empresa em **início de atividade**, RBT12 é proporcionalizado (RBT12p aparece no PGDAS-D).

## Relacionados

- [fator-r-e-anexos.md](fator-r-e-anexos.md)
- [limites-sublimites-e-exclusao.md](limites-sublimites-e-exclusao.md)
- [../patterns/calcular-das-mensal.md](../patterns/calcular-das-mensal.md)
- [../../documentos-fonte/concepts/pgdas-d-estrutura.md](../../documentos-fonte/concepts/pgdas-d-estrutura.md)
