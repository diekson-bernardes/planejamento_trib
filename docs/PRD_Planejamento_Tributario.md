# PRD — Plataforma de Planejamento Tributário

> Comparação entre Simples Nacional, Lucro Presumido e Lucro Real

| **Documento**          | **Definição**                                         |
|------------------------|-------------------------------------------------------|
| Versão                 | 1.0                                                   |
| Data-base              | 10 de setembro de 2026                                |
| Responsável de negócio | Diekson Porto Bernardes                               |
| Status                 | Especificação para desenvolvimento / MVP              |
| Público                | Escritórios contábeis, consultores tributários e PMEs |

**DADOS → VALIDAÇÃO → SIMULAÇÃO → COMPARAÇÃO → RECOMENDAÇÃO**

# 1. Resumo executivo

Produto web para receber documentos fiscais, trabalhistas e contábeis em PDF ou XLSX, extrair e conciliar os dados, projetar um exercício completo e comparar os custos dos três regimes tributários brasileiros. A plataforma deve indicar o regime economicamente mais vantajoso entre os juridicamente elegíveis, explicar os fatores da recomendação e preservar uma trilha de auditoria até o documento de origem.

A recomendação não será baseada apenas no menor total de tributos. O motor aplicará critérios de elegibilidade, confiança dos dados, risco fiscal, impacto sobre créditos na cadeia, sazonalidade, custo de conformidade e sensibilidade das premissas. O parecer final exigirá revisão e aprovação de profissional habilitado.

| **Elemento**      | **Definição**                                                                                                                            |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| Problema          | Comparações manuais são lentas, pouco padronizadas e vulneráveis a erros de classificação, períodos incompletos e regras desatualizadas. |
| Proposta de valor | Transformar relatórios heterogêneos em cenários comparáveis, reproduzíveis e explicáveis.                                                |
| Entrada mínima    | PGDAS-D, relatório de folha e dados contábeis, em PDF e/ou XLSX.                                                                         |
| Saída principal   | Quadro comparativo anual e mensal, regime recomendado, economia estimada, riscos, premissas e pendências.                                |
| Usuário decisor   | Contador ou consultor tributário; o cliente visualiza e aprova cenários, mas não altera regras legais.                                   |
| Princípio crítico | Nenhum regime inelegível pode ser apresentado como recomendação válida.                                                                  |

# 2. Objetivos e métricas de sucesso

## 2.1 Objetivos

- Reduzir o tempo de elaboração de uma análise comparativa sem sacrificar a revisão profissional.

- Padronizar a ingestão, classificação, projeção e documentação das premissas.

- Separar dados extraídos, dados informados, regras legais e ajustes manuais.

- Exibir não apenas o resultado, mas a memória de cálculo e a causa das diferenças.

- Permitir reprocessamento com nova legislação, mantendo a versão anterior reproduzível.

## 2.2 Indicadores do produto

| **Indicador**            | **Meta do MVP**                                                    | **Como medir**                                         |
|--------------------------|--------------------------------------------------------------------|--------------------------------------------------------|
| Completude de importação | ≥ 95% dos campos obrigatórios identificados em layouts homologados | Campos válidos / campos esperados                      |
| Conciliação de receita   | Diferença ≤ 1% ou pendência explícita                              | PGDAS × DRE/balancete × receita informada              |
| Rastreabilidade          | 100% dos valores do resultado com origem e regra                   | Drill-down da célula ao arquivo/página/linha           |
| Reprodutibilidade        | Mesmo conjunto + mesma regra = mesmo resultado                     | Hash de entradas, versão do motor e teste automatizado |
| Tempo de processamento   | Até 5 min para um dossiê padrão                                    | Upload até cenário disponível                          |
| Revisão humana           | 100% das recomendações com responsável e data                      | Log de aprovação                                       |
| Erros críticos           | Zero recomendação de regime impedido                               | Testes de elegibilidade e auditoria                    |

# 3. Escopo

## 3.1 Incluído no MVP

- Cadastro da empresa, estabelecimentos, atividades, município/UF e quadro societário essencial.

- Upload múltiplo de PDF e XLSX com identificação automática do tipo de relatório.

- Importação do PGDAS-D por período; relatório mensal de folha; balancete, DRE e razão/resumo contábil.

- Tela de revisão dos dados extraídos, com confiança, origem e ajuste justificado.

- Projeção de 12 meses por média, sazonalidade ou orçamento informado.

- Simulação de Simples Nacional, Lucro Presumido e Lucro Real.

- Comparação mensal/anual, análise de sensibilidade e recomendação explicável.

- Relatório final em PDF e exportação da memória de cálculo em XLSX.

- Versionamento de regras tributárias e trilha de auditoria.

## 3.2 Fora do MVP

- Transmissão de declarações ou geração oficial de guias.

- Substituição da escrituração contábil/fiscal ou do julgamento profissional.

- Planejamento societário internacional, preços de transferência e reorganizações complexas.

- Cálculo definitivo de benefícios fiscais sem parametrização e validação específica.

- Integração automática com e-CAC, eSocial, EFD ou ERPs; prevista para fases posteriores.

- Otimização baseada em alteração artificial de fatos, simulação ou ocultação de receita.

# 4. Personas, papéis e permissões

| **Papel**                   | **Pode fazer**                                                | **Restrições**                              |
|-----------------------------|---------------------------------------------------------------|---------------------------------------------|
| Administrador               | Configurar escritório, usuários, regras e versões             | Alterações de regra exigem publicação e log |
| Analista contábil/fiscal    | Importar, revisar, classificar, simular e comentar            | Não publica regra global                    |
| Revisor/Responsável técnico | Aprovar premissas e emitir recomendação                       | Assinatura vinculada à versão do cenário    |
| Cliente                     | Consultar resultados, anexar documentos e confirmar premissas | Não altera dados homologados nem regras     |
| Auditor                     | Consultar arquivos, memória e logs                            | Somente leitura                             |

# 5. Jornada principal

1.  Criar dossiê e definir ano-base e ano projetado.

2.  Cadastrar ou confirmar empresa, atividades, localização e vínculos societários.

3.  Importar PGDAS-D, folha e documentos contábeis.

4.  Classificar documentos, extrair campos e validar integridade.

5.  Conciliar receitas, folha, tributos e resultado; resolver divergências.

6.  Definir premissas de projeção e cenários.

7.  Executar elegibilidade e os três cálculos.

8.  Comparar resultados, testar sensibilidade e avaliar riscos.

9.  Revisor aprova ou devolve para correção.

10. Gerar relatório final e exportar memória de cálculo.

# 6. Entradas e modelo de dados

## 6.1 Documentos

| **Fonte**          | **Formatos** | **Campos mínimos**                                                                                | **Tratamento**                                                         |
|--------------------|--------------|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| PGDAS-D            | PDF, XLSX    | PA, RBT12, receitas segregadas, anexos, alíquota efetiva, tributos, DAS                           | Parser por layout; OCR somente se PDF imagem; aceitar múltiplos meses  |
| Folha              | PDF, XLSX    | Competência, salários, pró-labore, férias, 13º, encargos, RAT/FAP, terceiros, nº empregados       | Mapeamento de colunas; separar retenções do empregado e custo patronal |
| Contábil           | PDF, XLSX    | Plano de contas, saldos/débitos/créditos, DRE, receita, CMV/CSP, despesas, resultado, depreciação | Classificação para taxonomia comum; preservar conta original           |
| Cadastro/premissas | Tela, XLSX   | CNPJ, CNAEs, UF/município, sócios, início, benefícios, retenções, exportação, monofásicos/ST      | Validações cadastrais e confirmação manual                             |

## 6.2 Entidades essenciais

| **Entidade**       | **Campos-chave**                                                          |
|--------------------|---------------------------------------------------------------------------|
| company            | id, CNPJ, razão social, início, natureza jurídica, CNAEs, UF, município   |
| tax_case           | empresa, ano-base, ano projetado, status, responsável, versão             |
| source_file        | tipo, formato, hash, período, layout, páginas/abas, status, uploader      |
| extracted_value    | campo, valor, unidade, competência, confiança, arquivo, página/aba/célula |
| normalized_account | conta origem, taxonomia, natureza, dedutibilidade, regime/tributo         |
| assumption         | variável, valor, justificativa, fonte, autor, data                        |
| rule_version       | tributo, vigência, jurisdição, fórmula, fonte legal, aprovação            |
| simulation         | regime, cenário, versão de regra, entradas, resultados, alertas           |
| review             | responsável, decisão, ressalvas, data, hash do cenário                    |
| audit_event        | ator, evento, antes/depois, data/hora, IP/sessão                          |

# 7. Pipeline de importação e qualidade

O pipeline deve ser determinístico sempre que o layout for conhecido. Modelos de IA podem auxiliar classificação e extração de layouts desconhecidos, mas seus resultados nunca entram no cálculo sem validação de tipo, faixa, competência, totalização e confiança.

| **Etapa**         | **Comportamento obrigatório**                                | **Falha/saída**                               |
|-------------------|--------------------------------------------------------------|-----------------------------------------------|
| 1\. Recepção      | Antivírus, MIME real, tamanho, hash e duplicidade            | Rejeitar arquivo inseguro; alertar duplicado  |
| 2\. Classificação | Identificar documento, empresa e competência                 | Pedir classificação manual se confiança baixa |
| 3\. Extração      | Ler texto/tabelas/células e preservar coordenadas            | OCR para imagem; registrar método             |
| 4\. Normalização  | Datas, CNPJ, moeda, sinais, competências e taxonomia         | Marcar campo não mapeado                      |
| 5\. Validação     | Totais, subtotais, consistência temporal e regras de domínio | Bloqueante, alerta ou informativo             |
| 6\. Conciliação   | Comparar fontes independentes                                | Exigir justificativa acima da tolerância      |
| 7\. Homologação   | Usuário confirma dados e ajustes                             | Congelar versão para simulação                |

## 7.1 Regras mínimas de validação

- CNPJ e razão social compatíveis entre documentos.

- Competências sem lacunas ou duplicidades; períodos incompletos sinalizados.

- Soma das receitas segregadas igual à receita total do PGDAS, dentro da tolerância.

- DAS total compatível com a soma dos tributos componentes.

- Folha: remuneração + encargos + benefícios reconciliados com contas contábeis quando disponíveis.

- DRE fecha com o resultado; balancete equilibra débitos e créditos.

- Receitas negativas, despesas sem natureza, contas novas e saltos relevantes geram alertas.

- Ajuste manual exige motivo, anexo opcional e mantém valor original.

# 8. Motor tributário

O motor deve ser modular por tributo, regime, jurisdição e vigência. Fórmulas, faixas, limites e tratamentos especiais ficam em tabelas versionadas, nunca fixos na interface. Cada resultado armazenará a versão normativa utilizada.

## 8.1 Pré-validação de elegibilidade

| **Regime**       | **Verificações**                                                                                                                                                              |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Simples Nacional | Limite e proporcionalidade; atividades permitidas; composição societária; débitos/impedimentos informados; sublimites; início de atividade; receita global; anexos e Fator R. |
| Lucro Presumido  | Limite legal vigente; inexistência de hipótese de obrigatoriedade do Lucro Real; atividade; receitas e ganhos fora da presunção; opção anual.                                 |
| Lucro Real       | Admissibilidade/obrigatoriedade; qualidade da contabilidade; adições, exclusões, compensações, estimativas e controles fiscais.                                               |

## 8.2 Simples Nacional

- Calcular RBT12 mês a mês e aplicar anexo/faixa por atividade e receita segregada.

- Alíquota efetiva parametrizada: (RBT12 × alíquota nominal − parcela a deduzir) ÷ RBT12.

- Aplicar Fator R quando pertinente: folha e encargos dos 12 meses ÷ receita bruta dos 12 meses, conforme regra vigente.

- Tratar receitas monofásicas, substituição tributária, retenções, exportações, ISS fixo/retido e segregações cabíveis.

- Calcular contribuição patronal fora do DAS para atividades/anexos em que aplicável.

- Testar sublimites e excesso de receita; regime inelegível recebe status “não aplicável”, não valor zero.

## 8.3 Lucro Presumido

- Segregar receita por atividade e percentual de presunção de IRPJ e CSLL.

- Apurar IRPJ, adicional e CSLL por trimestre, com receitas/ganhos adicionados quando aplicável.

- Apurar contribuições sobre receita conforme regime cumulativo ou tratamento específico vigente.

- Calcular ISS e/ou ICMS/IPI segundo atividade, localização, produtos, créditos e benefícios parametrizados.

- Calcular encargos patronais da folha, RAT ajustado, terceiros e demais componentes aplicáveis.

- Considerar retenções recuperáveis/compensáveis separadamente do custo econômico.

## 8.4 Lucro Real

- Partir do resultado contábil conciliado e gerar ponte para lucro tributável.

- Classificar adições, exclusões, compensações, despesas indedutíveis, incentivos e diferenças temporárias.

- Permitir apuração trimestral ou anual com estimativas, quando juridicamente cabível.

- Apurar IRPJ, adicional e CSLL; controlar prejuízo fiscal e base negativa conforme limites vigentes.

- Apurar tributos sobre consumo no regime aplicável ao exercício, com créditos elegíveis e estornos.

- Calcular encargos patronais e tributos estaduais/municipais de modo equivalente ao cenário presumido.

## 8.5 Reforma Tributária

O produto deve suportar calendário de transição por exercício. CBS, IBS, Imposto Seletivo e a redução/extinção dos tributos substituídos serão módulos parametrizados. O comparativo deve informar se o cálculo é histórico, corrente ou projetado e quais alíquotas/regras estavam vigentes na versão utilizada. Para optantes do Simples, o sistema deve comportar as alternativas e efeitos creditórios previstos na legislação vigente, sem presumir neutralidade para clientes B2B.

# 9. Projeções e cenários

| **Método**      | **Uso**                                | **Regra**                                             |
|-----------------|----------------------------------------|-------------------------------------------------------|
| Realizado anual | 12 meses completos                     | Sem projeção; somente ajustes homologados             |
| Média simples   | Período parcial sem forte sazonalidade | Média mensal × meses faltantes                        |
| Sazonalidade    | Histórico ≥ 24 meses                   | Aplicar índice mensal histórico validado              |
| Orçamento       | Empresa possui forecast confiável      | Valores informados e identificados como premissa      |
| Cenários        | Incerteza relevante                    | Conservador, base e expansão com variáveis explícitas |

Variáveis de sensibilidade mínimas: receita, margem bruta, folha/pró-labore, relação folha/receita, despesas dedutíveis, créditos sobre insumos, mix de atividades, vendas B2B/B2C, ICMS/ISS e benefícios fiscais. A recomendação deve indicar o ponto de virada em que outro regime passa a ser mais vantajoso.

# 10. Comparação e recomendação

## 10.1 Métricas por regime

- Tributos totais e por espécie, mês e ano.

- Alíquota efetiva total sobre receita.

- Carga sobre consumo, renda e folha.

- Créditos apropriados, retidos e saldos transportados.

- Resultado líquido e caixa após tributos.

- Custo estimado de conformidade.

- Economia absoluta e percentual versus regime atual e segundo colocado.

- Elegibilidade, confiança dos dados e nível de risco.

## 10.2 Algoritmo de decisão

Regra padrão: escolher, entre os regimes elegíveis, aquele com menor custo tributário total ajustado pelos itens expressamente incluídos no escopo. A tela também apresentará resultado líquido e fluxo de caixa, para evitar uma conclusão baseada apenas em guia mensal. Custo de conformidade e riscos não serão ocultamente somados: aparecerão separadamente e poderão alterar a recomendação somente por política configurada e transparente.

| **Situação**                            | **Resultado do sistema**                                                 |
|-----------------------------------------|--------------------------------------------------------------------------|
| Um regime elegível e claramente menor   | Recomendar e demonstrar economia                                         |
| Diferença abaixo do limiar configurado  | “Resultado inconclusivo”; priorizar sensibilidade e fatores qualitativos |
| Dados críticos ausentes                 | Bloquear recomendação; permitir prévia identificada como incompleta      |
| Regime impedido                         | Mostrar motivo e fonte; excluir do ranking                               |
| Baixa confiança ou divergência material | Exigir revisão antes de emitir relatório                                 |
| Regra legal sem parametrização          | Não estimar silenciosamente; abrir pendência técnica                     |

## 10.3 Explicabilidade

A recomendação conterá: “recomendamos X porque...”; três principais fatores econômicos; condições jurídicas; economia estimada; intervalo de sensibilidade; riscos e premissas; dados ausentes; data-base normativa; responsável técnico. Cada número permitirá detalhar fórmula, base, alíquota, competência, regra e origem.

# 11. Telas e requisitos funcionais

| **ID** | **Requisito**                                            | **Prioridade** |
|--------|----------------------------------------------------------|----------------|
| RF-01  | Criar dossiê por empresa e exercício                     | Must           |
| RF-02  | Importar múltiplos PDF/XLSX com barra de progresso       | Must           |
| RF-03  | Classificar documento e detectar competência/duplicidade | Must           |
| RF-04  | Exibir campos extraídos lado a lado com a origem         | Must           |
| RF-05  | Editar valor com justificativa e log                     | Must           |
| RF-06  | Conciliar PGDAS, folha e contabilidade                   | Must           |
| RF-07  | Cadastrar premissas, benefícios e tratamentos especiais  | Must           |
| RF-08  | Validar elegibilidade antes do cálculo                   | Must           |
| RF-09  | Simular os três regimes com versão normativa             | Must           |
| RF-10  | Exibir comparação, composição e gráfico mensal           | Must           |
| RF-11  | Executar cenários e sensibilidade                        | Should         |
| RF-12  | Gerar PDF executivo e XLSX de memória                    | Must           |
| RF-13  | Fluxo elaborar → revisar → aprovar → emitir              | Must           |
| RF-14  | Duplicar cenário e comparar versões                      | Should         |
| RF-15  | Dashboard de pendências e alertas                        | Should         |

# 12. Requisitos não funcionais

| **Categoria**    | **Requisito**                                                                                                                         |
|------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| Segurança        | Criptografia em trânsito e repouso; segregação por tenant; MFA para perfis privilegiados; mínimo privilégio; logs protegidos.         |
| LGPD             | Finalidade, base legal definida pelo controlador, minimização, retenção configurável, atendimento a direitos e registro de operações. |
| Desempenho       | Uploads assíncronos; cálculo idempotente; resultado padrão em até 5 minutos.                                                          |
| Disponibilidade  | Meta inicial de 99,5%; fila com repetição segura; recuperação de falhas sem duplicar registros.                                       |
| Observabilidade  | Logs técnicos sem dados sensíveis, métricas de parser, falhas por layout, tempo e divergências.                                       |
| Auditabilidade   | Imutabilidade das versões emitidas; hash dos arquivos e cenário; histórico antes/depois.                                              |
| Acessibilidade   | Interface responsiva, teclado, contraste, rótulos e mensagens compreensíveis.                                                         |
| Manutenibilidade | Regras desacopladas do código, testes unitários por tributo e regressão com casos dourados.                                           |

# 13. Arquitetura lógica sugerida

| **Componente**           | **Responsabilidade**                                         |
|--------------------------|--------------------------------------------------------------|
| Frontend web             | Dossiê, uploads, revisão, comparação e aprovação             |
| API de aplicação         | Autenticação, autorização, workflow e contratos              |
| Armazenamento de objetos | Arquivos originais, derivados e relatórios                   |
| Fila/worker              | OCR, parsing, normalização, conciliação e exportação         |
| Banco relacional         | Cadastros, dados normalizados, regras, cenários e auditoria  |
| Serviço de documentos    | Detecção, extração determinística e auxílio por IA           |
| Motor tributário         | Elegibilidade, cálculo, projeção, sensibilidade e explicação |
| Serviço de regras        | Vigência, publicação, fonte legal, testes e rollback         |
| Relatórios               | PDF executivo e XLSX analítico                               |

Stack compatível com o contexto do projeto: aplicação web, PostgreSQL/Supabase, storage privado e workers de processamento. A escolha final deverá considerar isolamento por escritório, filas, volume de documentos e requisitos de residência/retensão de dados.

# 14. API e contratos essenciais

| **Rota conceitual**           | **Função**                 |
|-------------------------------|----------------------------|
| POST /cases                   | Criar dossiê               |
| POST /cases/{id}/files        | Registrar upload           |
| POST /files/{id}/process      | Enfileirar extração        |
| GET /files/{id}/extraction    | Obter campos e confiança   |
| PATCH /values/{id}            | Corrigir com justificativa |
| POST /cases/{id}/reconcile    | Executar conciliação       |
| POST /cases/{id}/eligibility  | Validar regimes            |
| POST /cases/{id}/simulations  | Executar cenários          |
| GET /simulations/{id}/explain | Memória e fatores          |
| POST /cases/{id}/reviews      | Aprovar/devolver           |
| POST /cases/{id}/reports      | Gerar entregáveis          |

# 15. Critérios de aceite

- Dado um PGDAS-D homologado, o sistema importa todas as competências e reconcilia receita total, receitas segregadas e DAS.

- Dado um XLSX com cabeçalhos diferentes, o usuário consegue mapear colunas e salvar o layout para reutilização.

- Dado um PDF escaneado, o sistema aplica OCR, indica menor confiança e exige conferência de campos críticos.

- Dada divergência de receita acima da tolerância, a simulação fica bloqueada até correção ou justificativa aprovada.

- Dada empresa acima do limite ou com impedimento cadastrado, o Simples aparece como inelegível e não é recomendado.

- Dada obrigatoriedade do Lucro Real, o Lucro Presumido aparece inelegível com motivo.

- Dada atividade sujeita ao Fator R, o cálculo usa folha e receita dos períodos corretos e mostra a memória mensal.

- Dado cenário de Lucro Real, toda adição/exclusão possui conta, valor, competência e justificativa.

- Dadas mesmas entradas e versão de regras, o motor retorna exatamente os mesmos resultados.

- Dada mudança normativa, cenário antigo continua reproduzível; novo cenário usa a nova versão.

- Dada recomendação emitida, PDF informa data-base, premissas, ressalvas, responsável e assinatura/aprovação.

- Dado qualquer valor do comparativo, o usuário chega ao documento e localização de origem quando aplicável.

# 16. Alertas e controles de risco

| **Risco**                        | **Controle**                                                                      |
|----------------------------------|-----------------------------------------------------------------------------------|
| Extração incorreta               | Layouts homologados, confidence score, validação aritmética e revisão humana      |
| Comparação incompleta            | Checklist por tributo e regime; status de cobertura no relatório                  |
| Regra desatualizada              | Vigência/versionamento, fonte oficial, aprovação e testes de regressão            |
| Receita mal segregada            | Taxonomia, validação por CNAE/operação e ajuste rastreável                        |
| Crédito indevido                 | Matriz de elegibilidade, documento suporte e bloqueio de premissa sem base        |
| Sazonalidade distorcida          | Cenários e comparação com histórico                                               |
| Recomendação automática indevida | Bloqueios, limiar de confiança e aprovação profissional                           |
| Vazamento de dados               | Tenant isolation, RLS quando aplicável, criptografia e controle de acesso         |
| Uso de IA sem evidência          | IA apenas assistiva; conservar trecho/célula de origem e validação determinística |

# 17. Roadmap

| **Fase**        | **Entrega**                                                 | **Saída de aceite**                            |
|-----------------|-------------------------------------------------------------|------------------------------------------------|
| 0 - Descoberta  | Amostras reais, layouts, matriz tributária e casos de teste | Catálogo de documentos e regra mínima aprovada |
| 1 - Fundação    | Cadastro, autenticação, dossiê, storage e auditoria         | Upload seguro e isolamento validado            |
| 2 - Importação  | Parsers PGDAS, folha e contábil; revisão e conciliação      | Dados homologados em taxonomia comum           |
| 3 - Cálculo MVP | Elegibilidade + três regimes + memória                      | Casos dourados conferidos pelo contador        |
| 4 - Decisão     | Comparação, projeção, sensibilidade e recomendação          | Relatório explicável aprovado                  |
| 5 - Escala      | Novos layouts, integrações, monitor normativo e analytics   | SLA e cobertura ampliados                      |

# 18. Questões abertas para decisão

- Quais atividades e UFs serão atendidas primeiro?

- Qual ano será o primeiro exercício oficial do motor?

- O MVP calculará ICMS por produto/NCM ou aceitará o valor fiscal consolidado?

- Quais layouts reais de folha e contabilidade serão homologados?

- Qual tolerância de conciliação por tipo de dado?

- Custo de conformidade participará do ranking ou será apenas exibido?

- Como serão aprovadas e publicadas novas versões legais?

- O relatório terá assinatura eletrônica ou apenas identificação do responsável?

- Qual política de retenção e exclusão dos documentos?

- Quais premissas podem ser editadas pelo cliente e quais apenas pelo contador?

# 19. Definição de pronto

Uma entrega é considerada pronta quando possui regra de negócio documentada, fonte legal e vigência quando aplicável, testes unitários e caso de regressão, validação de segurança, mensagens de erro úteis, trilha de auditoria, documentação operacional e aceite do responsável contábil. Nenhum cálculo tributário entra em produção apenas por passar em teste técnico.

# 20. Referências normativas e técnicas

- [Lei Complementar nº 123/2006 — Estatuto da ME/EPP e Simples Nacional](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm)

- [Lei nº 9.718/1998 — regras tributárias e hipóteses relacionadas ao Lucro Real](https://www.planalto.gov.br/ccivil_03/leis/l9718.htm)

- [Decreto nº 9.580/2018 — Regulamento do Imposto sobre a Renda](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/decreto/d9580.htm)

- [Lei Complementar nº 214/2025 — IBS, CBS, Imposto Seletivo e alterações correlatas](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm)

- [Código Tributário Nacional — Lei nº 5.172/1966](https://www.planalto.gov.br/ccivil_03/leis/l5172compilado.htm)

- [Portal do Simples Nacional — manuais do PGDAS-D](https://www8.receita.fazenda.gov.br/SimplesNacional/)

- [Receita Federal — Orientação Tributária](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria)

Nota de governança: as fontes acima definem a base do motor, mas não substituem legislação estadual, municipal, atos do CGSN, soluções de consulta, jurisprudência e normas vigentes específicas de cada exercício e operação.
