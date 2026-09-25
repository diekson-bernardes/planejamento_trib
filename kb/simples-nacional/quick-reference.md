# Simples Nacional — consulta rápida

> Para quem já entende o domínio e só precisa lembrar. Fonte das tabelas: Anexos I a V da LC 123/2006 (redação LC 155/2016), vigentes em 2026 sem alteração pela LC 214/2025 — transcrição conferida em mentorfiscal.com.br em 2026-09-24; conferir na norma antes de parametrizar o motor.

## Decisão rápida

| Se você quer... | Faça |
|---|---|
| Saber se o Simples pode ser comparado | [patterns/testar-elegibilidade-simples.md](patterns/testar-elegibilidade-simples.md) |
| Calcular o DAS de um mês | [patterns/calcular-das-mensal.md](patterns/calcular-das-mensal.md) |
| Saber se o serviço vai para o Anexo III ou V | Fator R ≥ 28% → III; < 28% → V ([concepts/fator-r-e-anexos.md](concepts/fator-r-e-anexos.md)) |

## Alíquota efetiva

`efetiva = (RBT12 × nominal − parcela a deduzir) ÷ RBT12` → aplicada sobre a receita do mês, por atividade.

## Anexos — alíquota nominal / parcela a deduzir (R$)

| Faixa (RBT12) | I Comércio | II Indústria | III Serviços | IV Serviços | V Serviços |
|---|---|---|---|---|---|
| 1: até 180.000 | 4,00% / 0 | 4,50% / 0 | 6,00% / 0 | 4,50% / 0 | 15,50% / 0 |
| 2: até 360.000 | 7,30% / 5.940 | 7,80% / 5.940 | 11,20% / 9.360 | 9,00% / 8.100 | 18,00% / 4.500 |
| 3: até 720.000 | 9,50% / 13.860 | 10,00% / 13.860 | 13,50% / 17.640 | 10,20% / 12.420 | 19,50% / 9.900 |
| 4: até 1.800.000 | 10,70% / 22.500 | 11,20% / 22.500 | 16,00% / 35.640 | 14,00% / 39.780 | 20,50% / 17.100 |
| 5: até 3.600.000 | 14,30% / 87.300 | 14,70% / 85.500 | 21,00% / 125.640 | 22,00% / 183.780 | 23,00% / 62.100 |
| 6: até 4.800.000 | 19,00% / 378.000 | 30,00% / 720.000 | 33,00% / 648.000 | 33,00% / 828.000 | 30,50% / 540.000 |

## Valores e limites que se esquece

| O quê | Valor | Observação |
|---|---|---|
| Teto EPP | R$ 4.800.000/ano | + até igual valor em exportação (art. 3º, § 14) |
| Teto ME | R$ 360.000/ano | Afeta enquadramento ME/EPP, não o cálculo do DAS |
| Sublimite ICMS/ISS | R$ 3.600.000/ano | Acima: ICMS/ISS fora do DAS (regras de efeito no tempo no conceito de limites) |
| Tolerância de excesso | 20% | Até 20%: efeito no ano seguinte; acima: no mês seguinte |
| Limite proporcional no início | R$ 400.000 × meses | Ano de início de atividade (teto) |
| Fator R | 28% | Folha 12 meses ÷ receita bruta 12 meses |
| Anexo IV | CPP fora do DAS | 20% + RAT sobre folha, recolhidos em GPS/DCTFWeb |
| Anexo I faixa 6 — repartição federal | IRPJ 13,5% · CSLL 10% · Cofins 28,27% · PIS 6,13% · CPP 42,10% | Confirmado ao recompor o DAS da amostra de jun/2026 |
| Anexo I faixa 5 — ICMS | 33,5% da efetiva | Usado para o ICMS quando a faixa 6 ainda recolhe ICMS no DAS |

## Erros comuns

| ❌ Não faça | ✅ Faça |
|---|---|
| Aplicar a alíquota nominal sobre a receita | Calcular a efetiva com a parcela a deduzir |
| Usar a receita do próprio mês no RBT12 | RBT12 = 12 meses **anteriores** ao período de apuração |
| Tratar toda a receita com um anexo só | Segregar por atividade, ST/monofásico, exportação, retenção |
| Mostrar Simples com valor zero quando inelegível | Mostrar "não aplicável" com o motivo |
| Esquecer a CPP do Anexo IV no custo total | Somar 20% + RAT sobre a folha fora do DAS |
| Aplicar o Fator R a atividade que não é do Anexo V | Fator R só decide entre V e III nas atividades do art. 18, § 5º-I |

## Onde procurar o resto

| Assunto | Arquivo |
|---|---|
| Começar do zero | [index.md](index.md) |
| Leitura do PGDAS-D | [../documentos-fonte/concepts/pgdas-d-estrutura.md](../documentos-fonte/concepts/pgdas-d-estrutura.md) |
| Simples após 2027 (IBS/CBS) | [../reforma-tributaria/concepts/simples-na-reforma.md](../reforma-tributaria/concepts/simples-na-reforma.md) |
