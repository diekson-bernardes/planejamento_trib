# BRAINSTORM: Importação e Conciliação de Documentos Fiscais

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|---|---|
| Feature | IMPORTACAO_CONCILIACAO |
| Date | 2026-09-24 |
| Author | brainstorm-agent |
| Status | Handoff Ready |

## Initial Idea

**Raw Input:** "Quero construir um sistema para planejamento tributário conforme PRD em anexo" (PRD: `docs/PRD_Planejamento_Tributario.md`, v1.0, data-base 10/09/2026).

**Context Gathered:**
- (Provided) O PRD descreve uma plataforma web completa: ingestão de PGDAS-D, folha e contábil (PDF/XLSX) → validação → conciliação → projeção → simulação de Simples Nacional, Lucro Presumido e Lucro Real → recomendação explicável com aprovação profissional. Stack sugerida: PostgreSQL/Supabase, storage privado e workers.
- (Provided) O primeiro ciclo SDD cobre somente a **importação e a conciliação** dos documentos. O motor tributário fica para um ciclo posterior.
- (Provided) Usuários do primeiro ciclo: **alguns escritórios contábeis parceiros (piloto)**, com isolamento de dados por escritório.
- (Provided) Folha e contábil vêm **somente do sistema Alterdata**, em **PDF com texto selecionável**.
- (Observed) O repositório tem apenas o PRD (`.md/.docx/.pdf`), `prompts/prompt01.md` (vazio), `kb/` (vazio) e amostras em `docs/Amostras/`. Não há código existente.
- (Observed) Folha, DRE e balancete foram gerados via "Microsoft: Print To PDF". O PGDAS-D foi gerado por iTextSharp 4.0.8 (Receita Federal).
- (Observed) `pdftotext -layout` embaralha colunas nesses PDFs. `pdfplumber`, reconstruindo linhas por coordenada (`top`), recompõe corretamente todas as linhas dos 4 tipos de documento.
- (Observed) No PGDAS-D, seção 2.2 (Receitas Brutas Anteriores), valor e competência seguinte vêm colados na extração (ex.: `92.916,6302/2025`). É preciso separá-los por regex.
- (Observed) Conciliação manual de ago/2026 fecha entre as fontes: receita PGDAS 203.180,77 = DRE "Vendas de Produtos" = balancete (205.577,54 C − 2.396,77 D); DAS 23.430,47 = DRE "Simples Nacional" = balancete [34009]; INSS 2.963,53 e FGTS 2.706,49 da folha = balancete; total de adicionais da folha 34.212,13 = crédito em Salários a Pagar [20401]; DAS de jul/2026 38.975,46 = saldo anterior de Simples Nacional a Recolher [20308].
- (Observed) A conta DRE "Salário" (27.777,47) ≠ rubrica "001 Salário Contratual" da folha (21.966,91). O agrupamento rubrica→conta difere, então a conciliação detalhada exige de-para.
- (Observed) As amostras contêm dados pessoais reais (CPF, RG, nomes de sócio e contador). Isso tem implicação de LGPD.
- (Inferred) Todos os escritórios do piloto usam Alterdata com os mesmos relatórios (Resumo Geral da Folha, DRE, Balancete Analítico).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|---|---|---|
| Likely Location | Repositório vazio (greenfield). Sugestão: `apps/web` (Next.js), `services/worker` (Python), `supabase/` (migrations) | Estrutura monorepo a definir no Design |
| Relevant KB Domains | `kb/` vazio. Domínios: PGDAS-D (layout Receita), relatórios Alterdata, plano de contas Alterdata, Simples Nacional (LC 123/2006) | Regras de validação dependem de conhecimento de layout; pode ser útil criar KB |
| IaC Patterns | N/A (nenhum observado) | Supabase (migrations) + container do worker a definir no Design |

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|---|---|---|
| 1 | Qual o maior problema que o primeiro entregável precisa resolver? | (b) Importação: extrair e conciliar PGDAS-D, folha e contábil | Ciclo restrito ao pipeline de ingestão; motor tributário fica para depois |
| 2 | Quem usará a primeira versão? | Inicialmente (a) só o escritório; **corrigido para (b) escritórios parceiros (piloto)** | Multi-tenant com RLS por escritório e papéis por escritório desde o MVP; sem cadastro público/cobrança |
| 3 | De quais sistemas saem os relatórios de folha e contábil? | Após duas mudanças (lista de 4 sistemas → variado → final): **somente Alterdata** | Parsers determinísticos por relatório Alterdata; sem mapeamento genérico nem IA para layouts desconhecidos |
| 4 | Em que formato os relatórios chegam? | (b) PDF com texto selecionável | Extração por texto/coordenadas; OCR e XLSX fora do MVP |
| 5 | O que precisa acontecer para considerar a importação pronta? | (c) Importação + conciliação + revisão/homologação (dados congelados) + exportação XLSX/JSON | A exportação homologada vira o contrato de entrada do futuro motor tributário |

## Sample Data Inventory

| Type | Location | Count | Notes |
|---|---|---:|---|
| Input files | `docs/Amostras/1.PGDASD-DECLARACAO-3770445620260{6,7,8}001.pdf` | 3 | PGDAS-D jun, jul, ago/2026. Empresa MACEDO COMERCIO (CNPJ 37.704.456/0001-42), 2 atividades (revenda com e sem ST), Fator r não se aplica |
| Input files | `docs/Amostras/2.Resumo da Folha.pdf` | 1 | Alterdata "Resumo Geral", ago/2026, 2 páginas (rubricas + GPS/FGTS/IRRF) |
| Input files | `docs/Amostras/3.DRE.pdf` | 1 | Alterdata DRE ago/2026, 2 páginas, com código de classificação |
| Input files | `docs/Amostras/Balancete.pdf` | 1 | Alterdata Balancete Analítico ago/2026, 3 páginas, saldo anterior/D/C/saldo atual com código de conta |
| Output examples | N/A | 0 | Nenhum modelo de exportação fornecido |
| Ground truth | N/A | 0 | Sem planilha conferida. Conciliação manual de ago/2026 (acima) serve de caso dourado inicial, a validar pelo contador |
| Related code | N/A | 0 | Greenfield |

**How samples will be used:**
- Referência de layout para os 4 parsers (âncoras de cabeçalho, colunas, rodapés).
- Casos dourados de regressão: valores extraídos e resultados de conciliação de ago/2026.
- Testes de validação interna: soma de tributos = DAS; adicionais − descontos = líquido; D = C no balancete.
- Versões anonimizadas devem substituir os originais em fixtures de teste (TBD).

## Approaches Explored

### Approach A: Parsers determinísticos em Python + Supabase + Next.js — Recommended

**Description:** Frontend Next.js; Supabase (Auth, Postgres com RLS por escritório, Storage privado, fila de jobs); worker Python que consome a fila e executa parsers `pdfplumber` por tipo de documento (PGDAS-D, Folha Alterdata, DRE Alterdata, Balancete Alterdata), gravando cada valor com página, bbox e versão do parser.

**Pros:**
- Técnica validada nas amostras (reconstrução por coordenadas funciona nos 4 tipos).
- 100% determinístico e reproduzível, conforme exige o PRD.
- `pdfplumber` é a biblioteca mais adequada para tabelas com coordenadas. Ecossistema Python favorece o futuro motor numérico, OCR e XLSX.

**Cons:**
- Duas linguagens (TypeScript + Python).
- Serviço adicional para hospedar (container do worker).

**Why Recommended:** O layout é fixo (Alterdata + PGDAS-D) e a rastreabilidade até página/posição é requisito central. Parsers determinísticos entregam isso com o menor risco.

### Approach B: Tudo em TypeScript (Next.js + Supabase Edge Functions + pdf.js)

**Description:** Extração com pdf.js dentro de Edge Functions; uma única linguagem e deploy.

**Pros:**
- Stack única, sem servidor adicional.

**Cons:**
- pdf.js entrega coordenadas cruas; a reconstrução de tabelas teria de ser feita manualmente.
- Limites de CPU e memória das Edge Functions.
- Ecossistema mais fraco para PDF e para o futuro motor numérico.

### Approach C: Extração via LLM (PDF → JSON) + validação determinística

**Description:** Um modelo de IA extrai os campos estruturados; validações aritméticas conferem o resultado.

**Pros:**
- Rápido para novos layouts; tolera variações de impressão.

**Cons:**
- Não determinístico; custo por documento; localização de origem imprecisa.
- Conflita com o princípio do PRD de IA apenas assistiva.
- Com escopo só Alterdata, a flexibilidade não compensa.

## Selected Approach

| Attribute | Value |
|---|---|
| Chosen | Approach A — Parsers determinísticos em Python + Supabase + Next.js |
| User Confirmation | Confirmado na conversa em 2026-09-24 ("opção A") |
| Reasoning | Layout fixo, necessidade de reprodutibilidade e rastreabilidade até a origem; técnica já validada nas amostras |

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|---|---|---|
| 1 | Primeiro ciclo = importação + conciliação + homologação + exportação | Importação é o gargalo apontado; a exportação vira contrato para o motor | Fluxo ponta a ponta reduzido; motor de cálculo primeiro |
| 2 | Multi-tenant (escritórios parceiros) desde o MVP, com RLS por escritório | Piloto com parceiros | Tenant único (escritório próprio); SaaS aberto |
| 3 | Escopo de origem: somente Alterdata + PGDAS-D | Decisão do usuário; habilita parsers fixos | Mapeamento genérico de colunas / múltiplos ERPs |
| 4 | Somente PDF com texto; sem OCR e sem XLSX | Formato real informado e observado | Suporte a XLSX e PDF escaneado |
| 5 | Extração por coordenadas (`pdfplumber`) | `pdftotext -layout` embaralha colunas nos PDFs Alterdata | Extração de texto linear |
| 6 | Divergência de conciliação acima da tolerância bloqueia a homologação até correção ou justificativa | Critério de aceite do PRD | Apenas alertar |
| 7 | Ajuste manual exige motivo e preserva o valor original | RF-05 do PRD, auditabilidade | Edição direta |
| 8 | Homologação gera snapshot imutável com hash | Reprodutibilidade para o motor futuro | Dados mutáveis após revisão |
| 9 | Conciliação da folha começa por totais (INSS, FGTS, proventos) com de-para de rubricas simplificado | Rubricas e contas se agrupam de forma diferente | De-para completo rubrica→conta no MVP |

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed/Deferred | Can Add Later? |
|---|---|---|
| Razão contábil | Sem amostra; balancete já traz a movimentação do mês | Yes |
| Papéis Revisor, Cliente, Auditor | Só são necessários com recomendação e emissão de parecer | Yes |
| Antivírus no upload | Uso restrito a parceiros; basta validar MIME e tamanho | Yes |
| OCR para PDF escaneado | Todos os PDFs têm texto | Yes |
| Importação de XLSX | Formato não utilizado pelo piloto | Yes |
| IA para classificação/extração de layouts desconhecidos | Somente Alterdata + PGDAS-D | Yes |
| Mapeamento genérico de colunas com layout salvo | Layout fixo | Yes |
| MFA e política de retenção configurável | Adiado até a expansão para mais escritórios | Yes |
| Motor tributário, projeção, sensibilidade, recomendação, PDF executivo | Pertencem ao ciclo seguinte | Yes |
| Cadastro público, planos e cobrança | Piloto fechado | Yes |

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---|---|---|---|
| Checkpoint 1: YAGNI, conceito, componentes (Web, Supabase, Worker Python, Conciliação, Auditoria) e limites | Yes | Aceito implicitamente (o usuário avançou para a próxima fase sem objeções) | No |
| Checkpoint 2: fluxo de dados (upload → recepção → classificação → extração → validações internas → conciliação → revisão → homologação → exportação), erros e dependências | Yes | "estão corretos" | No |

## Suggested Requirements for /define

### Problem Statement (Draft)

Escritórios contábeis gastam tempo e cometem erros ao transcrever e conciliar manualmente PGDAS-D e relatórios de folha e contábeis da Alterdata. Esses dados precisam chegar ao planejamento tributário extraídos, conciliados, rastreáveis até a origem e homologados.

### Target Users (Draft)

| User | Pain Point |
|---|---|
| Analista contábil/fiscal de escritório parceiro | Digitar e conferir manualmente valores de PDFs; conciliar receita, DAS e encargos entre fontes |
| Administrador do escritório | Controlar quem acessa os dados de cada cliente, com isolamento entre escritórios |
| Responsável de negócio (Diekson) | Base de dados homologada e confiável para o futuro motor tributário |

### Success Criteria (Draft)

- [ ] Os 6 PDFs de amostra são classificados automaticamente no tipo correto, com CNPJ e competência.
- [ ] Os valores extraídos de ago/2026 reproduzem a conciliação manual (receita 203.180,77; DAS 23.430,47; INSS 2.963,53; FGTS 2.706,49; proventos 34.212,13).
- [ ] 100% dos valores extraídos têm arquivo, página e posição de origem.
- [ ] Reprocessar o mesmo arquivo gera exatamente os mesmos valores (idempotência por hash).
- [ ] Divergência acima da tolerância bloqueia a homologação até correção ou justificativa.
- [ ] Usuário de um escritório não acessa dados de outro escritório (teste de RLS).
- [ ] Dossiê homologado exporta XLSX e JSON com hash do snapshot.
- [ ] Completude de importação ≥ 95% dos campos obrigatórios (meta do PRD para layouts homologados). Lista de campos obrigatórios por documento: TBD.
- [ ] Tempo de processamento de um dossiê padrão ≤ 5 min (meta do PRD). Definição de "dossiê padrão": TBD.
- [ ] Tolerâncias de conciliação por tipo de dado: TBD (questão aberta do PRD).

### Constraints Identified

- Origem: somente PGDAS-D (Receita) e relatórios Alterdata (Resumo Geral da Folha, DRE, Balancete Analítico).
- Formato: somente PDF com camada de texto.
- Stack: Next.js + Supabase (Auth, Postgres/RLS, Storage) + worker Python (`pdfplumber`).
- Multi-tenant por escritório; papéis Administrador e Analista.
- Processamento determinístico e reproduzível; IA fora do caminho de dados.
- LGPD: os documentos contêm dados pessoais (CPF/RG). Fixtures de teste devem usar cópias anonimizadas (TBD).
- Hospedagem do worker e plano do Supabase: TBD.
- Amostras disponíveis cobrem um único cliente e só ago/2026 para folha e contábil; mais meses e clientes: TBD.

### Out of Scope (Confirmed)

- Cálculo de Simples, Presumido e Real; elegibilidade; projeção; sensibilidade; recomendação; PDF executivo.
- OCR, XLSX, outros ERPs, IA para layouts desconhecidos, mapeamento genérico de colunas.
- Razão contábil.
- Papéis Revisor, Cliente e Auditor; MFA; retenção configurável; antivírus.
- Cadastro público, planos e cobrança.
- Integrações com e-CAC, eSocial, EFD e ERPs.

## Session Summary

| Metric | Value |
|---|---:|
| Questions Asked | 6 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 10 |
| Validations Completed | 2 |

## Next Step

Execute o **SDD Define by RDD**.
