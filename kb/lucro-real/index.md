# Lucro Real

> **Do que trata:** quem é obrigado ao Lucro Real, como o lucro contábil vira lucro tributável (adições, exclusões, compensações), apuração trimestral × anual por estimativa e PIS/Cofins não cumulativo.
> **Para quem:** quem simula o Real no comparativo ou monta a ponte contábil-fiscal no motor.
> **Última revisão:** 2026-09-24
> **Revisado por:** PENDENTE DE REVISÃO

## Comece por aqui

Leia `concepts/lucro-contabil-ao-tributavel.md`: o Real parte do resultado contábil, e a qualidade da contabilidade (balancete conciliado) decide se a simulação é confiável. Depois, `concepts/obrigatoriedade.md` para saber quando o Real não é escolha, e `patterns/apurar-irpj-csll-lucro-real.md` para executar.

## Conceitos — para entender

| Arquivo | Do que trata |
|---|---|
| [concepts/lucro-contabil-ao-tributavel.md](concepts/lucro-contabil-ao-tributavel.md) | Ponte e-Lalur/e-Lacs: adições, exclusões, compensação de prejuízo (trava de 30%) |
| [concepts/obrigatoriedade.md](concepts/obrigatoriedade.md) | Hipóteses do art. 14 da Lei 9.718/1998 e formas de apuração |
| [concepts/pis-cofins-nao-cumulativo.md](concepts/pis-cofins-nao-cumulativo.md) | 9,25% com créditos: o que gera crédito e o que não gera |

## Receitas — para fazer

| Arquivo | Resolve |
|---|---|
| [patterns/apurar-irpj-csll-lucro-real.md](patterns/apurar-irpj-csll-lucro-real.md) | Apurar IRPJ, adicional e CSLL de um período a partir do balancete |

## Consulta rápida

- [quick-reference.md](quick-reference.md) — alíquotas, travas, hipóteses de obrigatoriedade e erros comuns

## O que este domínio NÃO cobre

- Preços de transferência, lucros no exterior e subcapitalização (fora do MVP pelo PRD).
- Incentivos regionais (SUDAM/SUDENE), Lei do Bem, PAT em detalhe — citados apenas como exclusões/deduções possíveis.
- ICMS/IPI/ISS e a transição para CBS/IBS (ver `../reforma-tributaria/`).
- Escrituração da ECF/ECD passo a passo.

---

> **Responsabilidade:** a IA organizou e redigiu a partir de fontes públicas e conhecimento geral; quem responde pelo conteúdo é o profissional que revisar. As listas de adições e exclusões são exemplificativas — o RIR/2018 (Decreto 9.580/2018) é a referência.
