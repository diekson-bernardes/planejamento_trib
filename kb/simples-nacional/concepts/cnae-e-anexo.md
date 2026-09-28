# Do CNAE ao anexo do Simples (tabela do planejamento rápido)

> **O que é:** a tabela que o sistema usa para *sugerir* o anexo, a classe de presunção, o Fator R e as vedações a partir do CNAE principal da empresa, quando não há PGDAS-D para dizer em que anexo a receita foi declarada.
> **Fonte:** LC 123/2006 (art. 3º, § 4º; art. 17; art. 18, §§ 4º a 5º-J) e Resolução CGSN 140/2018, lidas via fontes secundárias em 2026-09-26. **Texto oficial não conferido** — `services/worker/rules/cnae_anexos.json` tem `verificado: false`.

## Por que isto existe

No dossiê completo o anexo vem das atividades declaradas no PGDAS-D. No planejamento rápido só há faturamento, folha e DRE; o CNAE (consultado na Receita pela automação n8n ou digitado) é o único indício da atividade. A tabela transforma esse indício em sugestão — **o analista confirma** o perfil nas premissas.

## Como funciona

- Casamento pelo **prefixo mais longo** dos 7 dígitos do CNAE: subclasse (7) › classe (4–5) › grupo (3) › divisão (2).
- Divisões 45–47 → Anexo I (comércio); 05–33 → Anexo II (indústria); construção (41–43), vigilância e limpeza → Anexo IV; serviços intelectuais (62, 70–74, 86) → Anexo V com Fator R; demais serviços listados → Anexo III.
- Exceções por classe: combustíveis (4681, 4731 → presunção de 1,6%), reparação de veículos (4520 → Anexo III).
- Vedações marcadas (`vedado: true`): fumo, armas, explosivos, bebidas alcoólicas no atacado ou na fabricação (salvo pequenos produtores), energia elétrica, factoring, instituições financeiras, locação de imóveis próprios e cessão de mão de obra. A sugestão avisa; a decisão é do analista.
- CNAE fora da tabela (ex.: agricultura) → **sem sugestão**: a recomendação fica bloqueada até o analista escolher o anexo.

## O que costuma ser confundido

| Isto | Não é isto |
|---|---|
| CNAE principal sugere o anexo de toda a receita | Receita dos CNAEs secundários distribuída automaticamente (adiado) |
| Tabela com versão e hash próprios | Parte das regras tributárias de 2026/2027 (não muda os goldens) |
| Vedação sinalizada na sugestão | Exclusão automática do Simples |

## Relacionados

- [fator-r-e-anexos.md](fator-r-e-anexos.md)
- [limites-sublimites-e-exclusao.md](limites-sublimites-e-exclusao.md)
