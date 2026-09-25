# Relatórios Alterdata: Folha, DRE e Balancete

> **O que é:** os três relatórios da Alterdata que o projeto importa — Resumo Geral da Folha, Demonstração do Resultado do Exercício e Balancete Analítico — gerados em PDF via "Microsoft: Print To PDF".
> **Fonte:** observação de um relatório de cada tipo (ago/2026, um cliente comercial) em 2026-09-24. **Nenhuma documentação oficial da Alterdata foi consultada**; layouts de outros clientes, meses ou versões do sistema não foram vistos.

## Por que isto existe

A folha e a contabilidade são as fontes de custo (folha, encargos) e de resultado (margem) que o motor usa para Presumido e Real. Elas também são o lado B da conciliação com o PGDAS.

## Como funciona

**Resumo Geral da Folha (2 páginas na amostra)**
- Cabeçalho: código interno e nome da empresa, CNPJ sem máscara, endereço, "Período", "Tipo Processo".
- Página 1: colunas ATIVOS | DEMITIDOS | AFASTADOS | TOTAL. Linhas de rubrica "código + descrição" (ex.: 001 Salário Contratual, 022 Hora Extra 60%, 400 Comissão, 903 INSS Folha, 914 IRRF Folha), depois TOTAL DE ADICIONAIS, TOTAL DE DESCONTOS, TOTAL LÍQUIDO A PAGAR, líquidos de férias e TOTAL DE FUNCIONÁRIOS.
- Página 2: GPS (empregados, sócios, autônomos, RAT, terceiros — patronal zerada para optante do Simples), FGTS (bases e valores), DARF de IRRF por origem, bases de aposentadoria especial e o texto "Empresa optante pelo SUPER SIMPLES".
- Códigos de rubrica podem repetir com descrições diferentes (ex.: "141" duas vezes): a chave natural não é única.

**DRE (2 páginas)**
- Colunas: Descrição | Classificação (ex.: 4.1.1.01.001) | Exercício Atual.
- Grupos em maiúsculas sem valor; contas analíticas com classificação e valor; subtotais com "=" e valores com asteriscos (`*****36.539,03D`).
- Sufixo D/C no valor; bloco final "RESULTADO DO EXERCÍCIO" com receitas, despesas + custo e lucro líquido.
- Página 1 traz as assinaturas do administrador e do contador (dados pessoais — não extrair).

**Balancete Analítico (3 páginas)**
- Colunas: Descrição | Saldo Anterior | Débito | Crédito | Saldo Atual.
- Código reduzido entre colchetes ao fim da descrição (ex.: "Simples Nacional a Recolher - [20308]"); a hierarquia vem pela indentação e pelo tipo (grupo em maiúsculas, analítica em caixa mista).
- Saldos com D/C; débito e crédito do período sem sufixo.
- O código do balancete (reduzido, ex.: 40101) é **diferente** da classificação da DRE (ex.: 4.1.1.01.001) para a mesma conta.

## O que costuma ser confundido

| Isto | Não é isto |
|---|---|
| Código reduzido do balancete ≠ classificação da DRE | Mesma chave nos dois relatórios |
| Asteriscos marcam subtotal | Asteriscos fazem parte do número |
| D/C indica natureza do saldo | D = negativo, C = positivo em qualquer conta |
| Patronal zerada na folha = optante do Simples | Empresa sem encargos |
| TOTAL DE ADICIONAIS = proventos brutos | Total líquido a pagar |

## Quando isto importa na prática

- **Mapeamento de contas:** as regras de conciliação precisam de de-para por empresa (vendas, Simples, INSS, FGTS, salários a pagar), com o código do balancete e a classificação da DRE.
- **"Print To PDF":** a posição do texto depende da impressão; o parser deve usar âncoras textuais e a ordem relativa das colunas, não coordenadas absolutas.
- **Margem para o motor:** o resultado da DRE só é confiável se o balancete fechar e a receita conciliar com o PGDAS.
- **LGPD:** nomes, CPF e RG aparecem nas assinaturas; o parser ignora esses blocos e os logs nunca registram texto do PDF.

## Relacionados

- [pgdas-d-estrutura.md](pgdas-d-estrutura.md)
- [../patterns/extrair-pdf-por-coordenadas.md](../patterns/extrair-pdf-por-coordenadas.md)
- [../../planejamento-comparativo/concepts/encargos-folha-por-regime.md](../../planejamento-comparativo/concepts/encargos-folha-por-regime.md)
