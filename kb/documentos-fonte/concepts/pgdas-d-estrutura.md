# Estrutura do extrato do PGDAS-D

> **O que é:** o PDF da declaração do PGDAS-D (Receita Federal), que registra por período de apuração as receitas, o RBT12, a segregação por atividade e os tributos que compõem o DAS.
> **Fonte:** observação de 3 declarações originais (jun, jul e ago/2026) de um cliente do projeto, geradas por iTextSharp 4.0.8, analisadas em 2026-09-24. Manuais oficiais do PGDAS-D no Portal do Simples Nacional não foram consultados nesta sessão.

## Por que isto existe

O PGDAS-D é a fonte mais padronizada do projeto: layout único nacional, texto selecionável e totais que se validam entre si. É a âncora da receita e do DAS na conciliação e a série histórica que alimenta o RBT12 e o Fator R do motor.

## Como funciona

| Seção | Conteúdo | Uso no sistema |
|---|---|---|
| Cabeçalho | Tipo (Original/Retificadora), Período de Apuração | Competência; retificação substitui a original |
| 1. Identificação | CNPJ matriz, nome, abertura, optante, regime de apuração (competência/caixa), nº da declaração | Validar CNPJ contra o dossiê |
| 2.1 Discriminativo de receitas | RPA, RBT12, RBT12p, RBA, RBAA, limite — mercado interno/externo/total | Receita do mês (R1), faixa, sublimite |
| 2.2 Receitas brutas anteriores | Série mensal de receitas (≈ 17 meses), interna e externa | Histórico para RBT12 móvel e projeção |
| 2.3 Folha de salários anteriores | Folha mensal usada no Fator R ("Nenhuma" se não aplicável) | Fator R |
| 2.4 Fator r | Valor ou "Não se aplica" | Conferência do anexo |
| 2.5 Valores fixos | ISS/ICMS fixos, se houver | Casos especiais |
| 2.6 Resumo | Receita bruta auferida e total do débito declarado | R2 (DAS) |
| 2.7 Por estabelecimento | UF, município, sublimite, "Impedido de recolher ICMS/ISS no DAS"; por atividade: descrição, receita informada, tributos (IRPJ, CSLL, Cofins, PIS, INSS/CPP, ICMS, IPI, ISS, Total) | Segregação por atividade; validação da soma |
| 2.8 Total geral | Débito declarado, suspenso e exigível por tributo | Total do DAS por tributo |
| 3. Recepção | Data/hora da transmissão, recibo, autenticação | Auditoria |

**Validações que fecham na amostra:** soma das receitas por atividade = RPA; soma dos tributos de cada atividade = total da atividade; soma das atividades = total do estabelecimento = total geral; exigível + suspenso = declarado.

**Atividades vistas na amostra:** revenda de mercadorias sem ST e com ST (ICMS zerado nesta). A descrição textual é longa e pode quebrar em várias linhas — o parser deve juntar as linhas até "Receita Bruta Informada".

## O que costuma ser confundido

| Isto | Não é isto |
|---|---|
| RPA = receita do mês (período de apuração) | RBT12 = receita do mês |
| 2.8 Total geral = DAS da competência | 2.6 "Valor total do débito" sempre igual a 2.8 (é, salvo suspensão) |
| Receita da seção 2.2 = meses anteriores | A série inclui o mês corrente |
| "Original" + "Retificadora" do mesmo PA | Duas competências diferentes |
| ICMS zero na atividade com ST | Erro de extração |

## Quando isto importa na prática

- **Parser:** as tabelas de tributos vêm como linha de cabeçalho + linha de valores; a seção 2.2 cola valor e competência seguinte. Separe por regex antes de interpretar.
- **Duplicidade:** o mesmo PA pode ter original e retificadora — mantenha a mais recente e registre a substituição (regra ainda a definir no produto).
- **Motor:** a seção 2.2 dá o histórico sem exigir PGDAS de todos os meses anteriores; a 2.3 dá a folha do Fator R.
- **Faixa 6:** a amostra está na faixa 6 com ICMS no DAS calculado pela faixa 5 — ver `../../simples-nacional/concepts/aliquota-efetiva-e-reparticao.md`.

## Relacionados

- [relatorios-alterdata.md](relatorios-alterdata.md)
- [../patterns/conciliar-fontes-por-competencia.md](../patterns/conciliar-fontes-por-competencia.md)
