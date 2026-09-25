# Testar a elegibilidade ao Simples Nacional

> **Resolve:** decidir, antes de simular custo, se o Simples pode ser opção válida no ano projetado — e registrar o motivo quando não pode.
> **Fonte:** LC 123/2006, arts. 3º e 17; PRD do projeto (§8.1, §10.2). Lista de vedações resumida — **conferir a lista completa na norma** antes de concluir por elegibilidade.

## Quando usar

- Antes de cada simulação do Simples no motor.
- Quando o cliente quer migrar para o Simples no próximo ano.
- Quando o cadastro societário ou as atividades mudam.

## Quando NÃO usar

- Para decidir se é **vantajoso** — isso é o comparativo ([../../planejamento-comparativo/patterns/comparar-regimes-exercicio.md](../../planejamento-comparativo/patterns/comparar-regimes-exercicio.md)).
- Para MEI.

## Passo a passo

1. **Natureza e sócios:** confirme que a empresa é sociedade empresária, simples, EIRELI/SLU ou empresário, e que **nenhum sócio é pessoa jurídica**. Se houver sócio PJ → inelegível.
2. **Participações dos sócios:** para cada sócio, liste outras empresas em que participa.
   - Outra empresa do Simples: some as receitas; acima de R$ 4,8 mi → inelegível.
   - Mais de 10% em empresa não optante: some as receitas; acima de R$ 4,8 mi → inelegível.
   - Sócio que é administrador de outra PJ com fins lucrativos: verificar a receita global.
3. **Atividades:** confira cada CNAE e cada atividade exercida contra as vedações do art. 17 (atividade financeira, cessão de mão de obra fora do Anexo IV, importação de combustíveis etc.). Atividade vedada → inelegível.
4. **Receita do ano projetado:** some a receita projetada mês a mês (mercado interno; exportação tem limite próprio).
   - ≤ R$ 4,8 mi → segue.
   - Entre R$ 4,8 mi e R$ 5,76 mi → elegível no ano, excluída no ano seguinte (registre o alerta).
   - Acima de R$ 5,76 mi → excluída a partir do mês seguinte ao excesso; o Simples só vale até lá.
5. **Receita do ano-base (entrada em janeiro):** para optar no ano projetado, a receita do ano anterior também não pode ter ultrapassado o teto.
6. **Sublimite:** verifique R$ 3,6 mi (e R$ 4,32 mi) na receita do ano para saber se ICMS/ISS ficam no DAS — isso não exclui, mas muda o cálculo.
7. **Débitos:** registre se há débito com a Fazenda ou o INSS sem exigibilidade suspensa (informado pelo cliente; o sistema não consulta o e-CAC).
8. **Início de atividade:** aplique os limites proporcionais (R$ 400.000 × meses).
9. **Resultado:** registre `elegível`, `elegível com alerta` ou `inelegível` com o motivo, a fonte (documento ou declaração) e a regra aplicada.

## Como saber que deu certo

- Toda simulação do Simples tem um status de elegibilidade com motivo e regra.
- Nenhum regime marcado `inelegível` aparece no ranking; ele aparece com o motivo.

## Quando dá errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Simples recomendado para quem tem sócio PJ | Cadastro societário não preenchido | Torne o quadro societário obrigatório antes do teste |
| Excluída no meio do ano projetado sem aviso | Teste feito só com o ano-base | Refaça o passo 4 com a projeção mês a mês |
| Custo do Simples muito baixo acima de R$ 3,6 mi | ICMS/ISS mantidos no DAS | Aplique o sublimite (passo 6) |
| Elegibilidade "sim" sem fonte | Declaração do cliente não registrada | Registre a premissa com autor e data |

## Relacionados

- [../concepts/limites-sublimites-e-exclusao.md](../concepts/limites-sublimites-e-exclusao.md)
- [../../planejamento-comparativo/concepts/elegibilidade-antes-do-custo.md](../../planejamento-comparativo/concepts/elegibilidade-antes-do-custo.md)
