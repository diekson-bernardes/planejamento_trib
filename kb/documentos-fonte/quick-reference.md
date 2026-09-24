# Documentos-fonte — consulta rápida

> Para quem já entende o domínio e só precisa lembrar. Fonte: observação das amostras do projeto em 2026-09-24 (um cliente, comércio, Alterdata) e DESIGN do ciclo 1.

## Classificação por âncora (página 1)

| Documento | Âncora de texto | Competência |
|---|---|---|
| PGDAS-D | "Programa Gerador do Documento de Arrecadação" | "Período de Apuração: dd/mm/aaaa a dd/mm/aaaa" |
| Folha Alterdata | "Resumo Geral" + "ADICIONAIS / DESCONTOS" | "Período: dd/mm/aaaa a dd/mm/aaaa" |
| DRE Alterdata | "Demonstração do Resultado do Exercício" | "de dd/mm/aaaa até dd/mm/aaaa" |
| Balancete Alterdata | "Balancete Analítico" | "de dd/mm/aaaa até dd/mm/aaaa" |

CNPJ: PGDAS com máscara (`00.000.000/0000-00`); Alterdata sem máscara (14 dígitos). Normalize antes de comparar.

## Regras de conciliação (tolerância padrão R$ 1,00)

| Regra | Lado A | Lado B |
|---|---|---|
| R1 Receita | PGDAS: RPA (receita do PA) | DRE: vendas; Balancete: crédito − débito da conta de vendas |
| R2 DAS | PGDAS: total do débito declarado | DRE: despesa Simples Nacional; Balancete: débito do período |
| R3 INSS | Folha: INSS dos empregados (GPS) | Balancete: crédito em INSS a Pagar |
| R4 FGTS | Folha: FGTS apurado | Balancete: crédito em FGTS a Pagar |
| R5 Proventos | Folha: TOTAL DE ADICIONAIS | Balancete: crédito em Salários a Pagar |
| R6 DAS anterior | PGDAS do mês m−1: total | Balancete do mês m: saldo anterior de Simples a Recolher |

Todas as seis fecharam com diferença zero em ago/2026 na amostra.

## Validações internas

| Documento | Deve fechar |
|---|---|
| PGDAS-D | Σ receita das atividades = RPA; Σ tributos = total por atividade; Σ atividades = total geral |
| Folha | Σ proventos = TOTAL DE ADICIONAIS; adicionais − descontos = líquido |
| DRE | Σ contas = subtotais "="; receitas − despesas = resultado |
| Balancete | Σ débitos = Σ créditos; saldo anterior ± D/C = saldo atual por conta |

## Armadilhas

| ❌ Não faça | ✅ Faça |
|---|---|
| Usar `pdftotext -layout` nos PDFs Alterdata | Reconstruir linhas por coordenada (`top`) |
| Ler "92.916,6302/2025" como um número | Separar valor e competência colados (seção 2.2 do PGDAS) |
| Ignorar asteriscos (`****203.180,77C`) | Remover `*` antes do parse; guardar D/C |
| Tratar D/C como sinal fixo | D/C depende da natureza da conta |
| Conciliar a receita pelo crédito bruto de vendas | Usar crédito − débito (devoluções) |
| Presumir "Salário" da DRE = rubrica 001 da folha | Os agrupamentos diferem; concilie pelos totais |
| Usar a patronal zerada da folha do Simples como custo em outro regime | Recalcular encargos por regime |

## Onde procurar o resto

| Assunto | Arquivo |
|---|---|
| Começar do zero | [index.md](index.md) |
| Regra de ICMS na faixa 6 do PGDAS | [../simples-nacional/concepts/aliquota-efetiva-e-reparticao.md](../simples-nacional/concepts/aliquota-efetiva-e-reparticao.md) |
