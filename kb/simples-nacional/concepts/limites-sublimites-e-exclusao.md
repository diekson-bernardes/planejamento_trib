# Limites, sublimites e exclusão

> **O que é:** os tetos de receita que definem se a empresa pode ficar no Simples (R$ 4,8 mi) e se ICMS/ISS continuam no DAS (sublimite de R$ 3,6 mi), e quando o excesso produz efeito.
> **Fonte:** LC 123/2006, arts. 3º, 13, 17, 19, 20, 30 e 31; conferência de valores em fontes secundárias em 2026-09-24. As datas de efeito abaixo são o entendimento usual — **confirmar na norma e na Resolução CGSN nº 140/2018** antes de usar em parecer.

## Por que isto existe

Recomendar o Simples para quem vai estourar o teto no ano projetado é o erro crítico que o PRD proíbe ("nenhum regime inelegível pode ser recomendado"). Limite não é detalhe de cálculo: é pré-condição.

## Como funciona

**Teto (R$ 4.800.000 por ano-calendário):**

| Receita do ano | Efeito |
|---|---|
| Até R$ 4,8 mi | Permanece |
| Acima de R$ 4,8 mi até R$ 5,76 mi (20%) | Excluída a partir de 1º de janeiro do ano seguinte |
| Acima de R$ 5,76 mi | Excluída a partir do mês seguinte ao excesso |

Receitas de exportação têm limite adicional de igual valor (art. 3º, § 14).

**Sublimite estadual/municipal (R$ 3.600.000):**

| Receita do ano | Efeito |
|---|---|
| Até R$ 3,6 mi | ICMS/ISS no DAS |
| Acima de R$ 3,6 mi até R$ 4,32 mi (20%) | ICMS/ISS fora do DAS a partir do ano seguinte |
| Acima de R$ 4,32 mi | ICMS/ISS fora do DAS a partir do mês seguinte |

Fora do DAS, ICMS e ISS seguem as regras normais do estado e do município (débito e crédito do ICMS, alíquota do ISS local), enquanto os tributos federais continuam no DAS.

**Início de atividade:** os limites são proporcionais — R$ 400.000 (teto) e R$ 300.000 (sublimite) por mês de atividade no ano.

**Vedações (art. 17), além da receita** — exemplos: sócio pessoa jurídica; sócio com mais de 10% em outra empresa não optante cuja receita global ultrapasse o teto; titular/sócio que participa de outra empresa do Simples com receita somada acima do teto; cessão de mão de obra (salvo exceções do Anexo IV); débitos com exigibilidade não suspensa; certas atividades financeiras. Lista completa: LC 123, arts. 3º, § 4º, e 17.

## O que costuma ser confundido

| Isto | Não é isto |
|---|---|
| Teto e sublimite medidos pela receita do ano-calendário | Medidos pelo RBT12 |
| RBT12 define a faixa | RBT12 define a exclusão |
| Até 20% de excesso: efeito no ano seguinte | Qualquer excesso exclui no mês seguinte |
| Receita global do grupo (sócios comuns) pode vedar | Só a receita da própria empresa importa |
| Inelegível = "não aplicável" no comparativo | Inelegível = custo zero |

## Quando isto importa na prática

- **Ano projetado:** some a receita projetada mês a mês; se cruzar R$ 4,8 mi, o Simples só vale até o mês de efeito da exclusão (ou nem entra, se acima de 20%).
- **Sublimite no ano projetado:** mesmo elegível, o custo muda porque ICMS/ISS saem do DAS — a simulação precisa calcular ICMS/ISS pelo regime normal.
- **Grupo econômico:** o cadastro societário (PRD §6.1) é insumo obrigatório do teste de elegibilidade.
- A amostra do projeto mostra RBAA R$ 3,48 mi e RBT12 R$ 3,84 mi: faixa 6, mas sublimite ainda sem efeito — exatamente o caso em que o ICMS segue no DAS calculado pela faixa 5.

## Relacionados

- [../patterns/testar-elegibilidade-simples.md](../patterns/testar-elegibilidade-simples.md)
- [aliquota-efetiva-e-reparticao.md](aliquota-efetiva-e-reparticao.md)
- [../../planejamento-comparativo/concepts/elegibilidade-antes-do-custo.md](../../planejamento-comparativo/concepts/elegibilidade-antes-do-custo.md)
