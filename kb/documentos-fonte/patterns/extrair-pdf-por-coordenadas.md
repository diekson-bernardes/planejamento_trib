# Extrair linhas de PDF por coordenadas

> **Resolve:** obter as linhas corretas (descrição + colunas de valor) de PDFs gerados via "Print To PDF", nos quais a extração de texto linear embaralha as colunas.
> **Fonte:** teste direto nas 6 amostras do projeto em 2026-09-24 com `pdfplumber` 0.11.10 (Python 3.14): `pdftotext -layout` desalinhou valores de outras linhas; o agrupamento de palavras por `top` com tolerância de 2,5 pt recompôs 100% das linhas visíveis dos 4 tipos.

## Quando usar

- Parsers dos relatórios Alterdata e do PGDAS-D.
- Qualquer PDF com texto selecionável cujas colunas saiam fora de ordem.

## Quando NÃO usar

- PDF sem camada de texto (escaneado) → rejeite; OCR está fora do MVP.
- Tabelas com linhas de grade confiáveis → `extract_tables` pode bastar (não é o caso dos PDFs da amostra).

## Passo a passo

1. **Abra com pdfplumber** e confira se alguma página tem texto (`extract_text()` não vazio). Sem texto → erro `NO_TEXT`.
2. **Extraia as palavras** de cada página com `extract_words(use_text_flow=False)`; cada palavra tem `text`, `x0`, `x1`, `top`, `bottom`.
3. **Ordene** por (`top`, `x0`).
4. **Agrupe em linhas:** comece uma linha nova quando `abs(top − top da 1ª palavra da linha atual) > 2,5`.
5. **Ordene cada linha** por `x0` e guarde página (base 1) e bbox (mín x0, mín top, máx x1, máx bottom).
6. **Localize as âncoras** do documento (cabeçalhos de seção, títulos de coluna). Âncora ausente → erro `LAYOUT` com a versão do parser, sem gravar valores parciais.
7. **Identifique as colunas pela ordem** dos tokens numéricos no fim da linha (ex.: balancete = saldo anterior, débito, crédito, saldo atual), não por x absoluto.
8. **Normalize os números:** remova `*`; separe o sufixo D/C; troque `.` de milhar e `,` decimal; use Decimal, nunca float.
9. **Trate células coladas:** no PGDAS 2.2, separe `valor + mm/aaaa` com regex antes de tokenizar.
10. **Grave cada valor** com página, bbox, seção, campo, rótulo, código de conta/rubrica, natureza e ordinal sequencial.
11. **Valide os totais internos** do documento antes de aceitar a extração.

## Como saber que deu certo

- Todas as linhas visíveis do PDF aparecem na ordem, com as colunas certas.
- As validações internas fecham (ex.: Σ rubricas = TOTAL DE ADICIONAIS; débito = crédito no balancete).
- Reprocessar o mesmo arquivo gera exatamente o mesmo conjunto de valores (mesmo hash de resultado).

## Quando dá errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Duas linhas visuais fundidas numa só | Tolerância alta ou fonte pequena | Reduza a tolerância; confira pelo bbox |
| Uma linha visual partida em duas | Valor impresso ligeiramente deslocado | Aumente a tolerância para 3 pt; valide pelo total |
| Coluna trocada (débito no crédito) | Célula vazia na linha | Use a posição x relativa ao cabeçalho da coluna como desempate |
| Número inválido `92.916,6302/2025` | Célula colada do PGDAS | Aplique a separação do passo 9 |
| Grupo lido como conta analítica | Hierarquia não detectada | Use caixa alta e ausência de classificação como sinal de grupo |

## Relacionados

- [../concepts/relatorios-alterdata.md](../concepts/relatorios-alterdata.md)
- [../concepts/pgdas-d-estrutura.md](../concepts/pgdas-d-estrutura.md)
- DESIGN do projeto: `sdd/DESIGN_IMPORTACAO_CONCILIACAO.md` (Patterns 1 e 2)
