# O Simples Nacional na reforma: por dentro ou regime regular

> **O que é:** a escolha que o optante do Simples passa a ter a partir de 2027 — recolher IBS/CBS dentro do DAS (modelo tradicional) ou pelo regime regular, fora do DAS (modelo "híbrido"), com efeito direto no crédito que seus clientes aproveitam.
> **Fonte:** LC 214/2025 (art. 41, § 3º, segundo as fontes) e LC 123/2006 alterada; lidos via e-auditoria.com.br, escolasuperioresn.com.br, cgmlaw.com.br e pfpadvogados.com.br em 2026-09-24. **Dispositivos não conferidos na fonte primária**; prazos de opção dependem de regulamentação do CGSN.

## Por que isto existe

O PRD pede: "Para optantes do Simples, o sistema deve comportar as alternativas e efeitos creditórios previstos na legislação vigente, sem presumir neutralidade para clientes B2B." Hoje, quem compra de um fornecedor do Simples e está no Real toma crédito de PIS/Cofins de 9,25% sobre a compra. Com a CBS, o crédito do comprador passa a se limitar ao que o fornecedor efetivamente recolheu — e no DAS isso é pouco.

## Como funciona

| Aspecto | Simples "por dentro" | Simples híbrido (regime regular de IBS/CBS) |
|---|---|---|
| IRPJ, CSLL, CPP (e IPI) | No DAS | No DAS |
| IBS e CBS | No DAS, pela parcela da alíquota efetiva | Fora do DAS, pelas regras não cumulativas |
| Créditos nas compras | Não apropria | Apropria créditos de IBS/CBS |
| Crédito do cliente B2B | Limitado ao valor de IBS/CBS pago no DAS | Integral, pela alíquota do regime regular |
| Complexidade | Baixa | Maior (apuração de débito e crédito, obrigações do regime regular) |
| Periodicidade da opção | — | Semestral (setembro → 1º semestre seguinte; março → 2º semestre, segundo as fontes) |

**Primeira janela:** a opção para o 1º semestre de 2027 é feita em setembro de 2026 (fontes citam prazo até 30/09/2026). Na data desta revisão (24/09/2026), a janela está aberta — **confirmar o prazo no Portal do Simples Nacional**.

## O que costuma ser confundido

| Isto | Não é isto |
|---|---|
| Híbrido: só IBS/CBS saem do DAS | Híbrido: a empresa sai do Simples |
| Crédito do cliente limitado ao pago no DAS | Crédito integral como hoje no PIS/Cofins |
| Opção semestral | Opção anual e irretratável como a do Simples |
| B2C: o cliente final não toma crédito | Híbrido é vantajoso para qualquer empresa |

## Quando isto importa na prática

- **Clientes B2B no Real/Presumido (ou no regime regular):** o híbrido preserva a competitividade do fornecedor do Simples — o cliente não perde crédito.
- **Vendas ao consumidor final (B2C):** o crédito do cliente não importa; o Simples por dentro tende a ser mais barato e mais simples.
- **Empresa com muitas compras tributadas:** o híbrido permite recuperar créditos, o que pode compensar a alíquota maior.
- **Motor:** a simulação do Simples a partir de 2027 precisa de dois sub-cenários (por dentro × híbrido) e do perfil de clientes (percentual B2B que aproveita crédito).

## Como o sistema calcula 2027 (hipóteses em aberto)

| Ponto | Tratamento nas regras `2027.1.0` | Situação |
|---|---|---|
| Repartição do DAS em 2027 (A-401) | Mesma alíquota efetiva do anexo de 2026; as parcelas de PIS + Cofins passam a ser de CBS e o IBS fica sem parcela no DAS | Hipótese — fontes secundárias não trazem a tabela de 2027 |
| Híbrido | O DAS perde as parcelas de CBS/IBS; CBS/IBS apurados como no regime regular (débito − crédito financeiro, saldo credor transportado) | Hipótese — opção tratada como anual (a semestral fica para outro ciclo) |
| Base de CBS/IBS | Receita − monofásica/isenta − ICMS/ISS do regime no mês − exclusões informadas | LC 214/2025, art. 12, § 2º (ICMS/ISS fora da base), segundo as fontes; o sistema usa o ICMS/ISS calculado pelo regime (líquido), não o destacado nas notas |
| Alíquotas de 2027 | Premissa do escritório, sem padrão (a de referência depende de resolução do Senado) | Sem valor, a projeção de 2027 sai bloqueada |

**Fonte:** LC 214/2025 lida via fontes secundárias (as mesmas do topo desta nota) em 2026-09-25; **texto oficial não conferido** — todas as regras de 2027 têm `verificado: false` até a revisão contábil.

## Relacionados

- [calendario-transicao.md](calendario-transicao.md)
- [../patterns/avaliar-opcao-regime-regular-simples.md](../patterns/avaliar-opcao-regime-regular-simples.md)
- [../../simples-nacional/index.md](../../simples-nacional/index.md)
