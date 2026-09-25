# Documentos-fonte e Conciliação

> **Do que trata:** como ler o PGDAS-D e os relatórios Alterdata (Resumo Geral da Folha, DRE, Balancete Analítico) em PDF, e como conciliar essas fontes entre si por competência.
> **Para quem:** quem implementa ou mantém os parsers e a conciliação (ciclo 1 do projeto), e o analista que revisa divergências.
> **Última revisão:** 2026-09-24
> **Revisado por:** PENDENTE DE REVISÃO

## Comece por aqui

Leia `concepts/pgdas-d-estrutura.md` e `concepts/relatorios-alterdata.md` para saber o que cada documento contém e onde estão as armadilhas de extração. Para executar, `patterns/extrair-pdf-por-coordenadas.md` (parser) e `patterns/conciliar-fontes-por-competencia.md` (regras R1–R6).

## Conceitos — para entender

| Arquivo | Do que trata |
|---|---|
| [concepts/pgdas-d-estrutura.md](concepts/pgdas-d-estrutura.md) | Seções do extrato do PGDAS-D, campos e validações internas |
| [concepts/relatorios-alterdata.md](concepts/relatorios-alterdata.md) | Folha, DRE e balancete da Alterdata: estrutura, códigos, natureza D/C |

## Receitas — para fazer

| Arquivo | Resolve |
|---|---|
| [patterns/extrair-pdf-por-coordenadas.md](patterns/extrair-pdf-por-coordenadas.md) | Extrair linhas corretas de PDFs "Print To PDF" cujo texto sai embaralhado |
| [patterns/conciliar-fontes-por-competencia.md](patterns/conciliar-fontes-por-competencia.md) | Conciliar receita, DAS, INSS, FGTS e proventos entre PGDAS, folha e contabilidade |

## Consulta rápida

- [quick-reference.md](quick-reference.md) — âncoras de classificação, regras de conciliação e armadilhas

## O que este domínio NÃO cobre

- Outros ERPs (Domínio, Questor etc.), XLSX e PDF escaneado (OCR) — fora do MVP.
- Razão contábil, EFD, eSocial e DCTFWeb.
- Cálculo dos tributos: ver os domínios de cada regime.

---

> **Fonte principal:** observação direta das 6 amostras reais do projeto (`docs/Amostras/`, 3 PGDAS-D de jun–ago/2026 e folha, DRE e balancete de ago/2026 de um único cliente, comércio), analisadas em 2026-09-24. **Layouts de outros clientes ou meses não foram vistos** — trate as regras como hipóteses até haver mais amostras. Nenhum dado pessoal das amostras foi copiado para esta base.
