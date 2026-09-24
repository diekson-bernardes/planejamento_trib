# Planejamento comparativo — consulta rápida

> Para quem já entende o domínio e só precisa lembrar. Fontes: PRD do projeto (§8–10), LC 123/2006, Leis 9.249/1995, 9.718/1998, 8.212/1991, 15.270/2025, LC 224/2025. As heurísticas são prática de mercado — **não são regra legal** e não substituem a simulação.

## Decisão rápida

| Situação | Tendência (confirmar simulando) |
|---|---|
| Regime inelegível | Fora do ranking, com motivo — sempre |
| Serviço do Anexo V com folha ≥ 28% da receita | Simples (Anexo III) costuma vencer |
| Serviço com folha baixa e margem alta | Presumido costuma vencer o Simples do Anexo V |
| Comércio com margem líquida baixa (< ~8%) e muitas compras | Real (créditos de PIS/Cofins + lucro baixo) |
| Prejuízo ou margem muito volátil | Real (anual com suspensão) |
| Receita perto de R$ 4,8 mi no ano projetado | Testar a exclusão do Simples mês a mês |
| Receita acima de R$ 5 mi no Presumido | Refazer com a LC 224/2025 (presunção +10% no excedente) |
| Cliente B2B que dá crédito ao comprador | Considerar o efeito crédito (Real/Presumido geram mais crédito que o Simples) |
| Diferença entre os dois melhores < limiar configurado | "Resultado inconclusivo" (PRD §10.2) |

## Custo total a comparar (por regime)

| Componente | Simples | Presumido | Real |
|---|---|---|---|
| IRPJ/CSLL | No DAS | Presunção | Lucro ajustado |
| PIS/Cofins | No DAS | 3,65% cumulativo | 9,25% − créditos |
| ICMS/ISS | No DAS (até o sublimite) | Regime normal | Regime normal |
| CPP patronal (20%) | No DAS (exceto Anexo IV) | Sobre a folha | Sobre a folha |
| RAT × FAP | No DAS (exceto Anexo IV) | 1–3% × FAP | 1–3% × FAP |
| Terceiros (Sistema S, salário-educação) | Dispensado | ~5,8% (varia por FPAS) | ~5,8% (varia por FPAS) |
| FGTS 8% | Sim | Sim | Sim (não é tributo, mas é custo; igual nos três) |
| Pró-labore: 20% patronal | No DAS (exceto IV) | Sim | Sim |

## Valores de 2026 que mudam a remuneração dos sócios

| O quê | Valor | Fonte |
|---|---|---|
| Dividendos isentos de retenção | Até R$ 50.000/mês por PJ pagadora a cada PF | Lei 15.270/2025 |
| IRRF sobre dividendos acima do limite | 10% | Lei 15.270/2025 |
| IRPF mínimo (IRPFM) | Renda anual > R$ 600 mil; até 10% a partir de R$ 1,2 mi | Lei 15.270/2025 |
| Redutor da carga combinada PJ + PF | Limite de 34% (PJ em geral) | Lei 15.270/2025 |
| IRRF sobre JCP | 17,5% | LC 224/2025 |
| Isenção IRPF mensal | Até R$ 5.000 (redução até R$ 7.350) | Lei 15.270/2025 |

## Erros comuns

| ❌ Não faça | ✅ Faça |
|---|---|
| Comparar só a "guia mensal" | Comparar o custo total (DAS/DARF + folha + ICMS/ISS) e o caixa |
| Somar retenções como custo | Retenção é antecipação; mostrar à parte |
| Somar custo de conformidade ao imposto escondido | Exibir separado; só afeta o ranking por política configurada |
| Esquecer o comprador B2B | Avaliar o crédito que o regime transfere ao cliente |
| Usar a margem de um ano atípico | Cenários conservador/base/expansão |
| Estimar sem regra parametrizada | Abrir pendência técnica (PRD §10.2) |

## Onde procurar o resto

| Assunto | Arquivo |
|---|---|
| Começar do zero | [index.md](index.md) |
| DAS | [../simples-nacional/patterns/calcular-das-mensal.md](../simples-nacional/patterns/calcular-das-mensal.md) |
| Presumido | [../lucro-presumido/patterns/calcular-trimestre-presumido.md](../lucro-presumido/patterns/calcular-trimestre-presumido.md) |
| Real | [../lucro-real/patterns/apurar-irpj-csll-lucro-real.md](../lucro-real/patterns/apurar-irpj-csll-lucro-real.md) |
