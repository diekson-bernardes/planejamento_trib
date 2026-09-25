# DEFINE: Importação e Conciliação de Documentos Fiscais

> Plataforma web multi-escritório que importa PDFs do PGDAS-D e de relatórios Alterdata (Folha, DRE, Balancete), extrai todas as linhas com rastreabilidade até a origem, concilia as fontes por competência e homologa um snapshot imutável exportável em XLSX/JSON para o futuro motor tributário.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | IMPORTACAO_CONCILIACAO |
| **Date** | 2026-09-24 |
| **Author** | SDD Define by RDD (responsável de negócio: Diekson Porto Bernardes) |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Analistas de escritórios contábeis parceiros transcrevem e conferem manualmente os valores do PGDAS-D e dos relatórios de folha e contábeis da Alterdata, e depois conciliam receita, DAS e encargos entre essas fontes. O processo é lento e sujeito a erro, e não deixa a base de dados homologada e rastreável até a origem de que o planejamento tributário (comparação entre Simples, Presumido e Real) precisa.

---

## Target Users

| User | Role | Pain Point |
|---|---|---|
| Analista contábil/fiscal | Usuário de escritório parceiro que importa, revisa, ajusta e homologa dossiês | Digitar e conferir valores de PDFs; conciliar receita, DAS, INSS, FGTS e proventos entre PGDAS, folha e contabilidade |
| Administrador do escritório | Configura o escritório, usuários e parâmetros (tolerância) | Garantir que apenas o próprio escritório acessa os dados dos seus clientes |
| Responsável de negócio / futuro motor tributário | Consumidor do snapshot homologado | Precisa de dados congelados, versionados e rastreáveis como entrada do cálculo dos regimes |

---

## Goals

| Priority | Goal |
|---|---|
| **MUST** | Isolar dados por escritório (tenant) com RLS; papéis Administrador e Analista |
| **MUST** | Cadastrar empresa (CNPJ, razão social) e criar dossiê por empresa e período |
| **MUST** | Upload múltiplo de PDFs com registro de SHA-256, detecção de duplicidade e rejeição de PDF sem camada de texto |
| **MUST** | Classificar automaticamente o documento (PGDAS-D, Folha Alterdata, DRE Alterdata, Balancete Analítico Alterdata) e extrair CNPJ e competência |
| **MUST** | Extrair todas as linhas de cada documento, com arquivo, página, bbox, método e versão do parser |
| **MUST** | Validar totais internos de cada documento |
| **MUST** | Conciliar as fontes por competência com tolerância configurável (padrão R$ 1,00) e bloquear a homologação acima da tolerância |
| **MUST** | Tela de revisão com o valor ao lado da origem; ajuste manual com motivo obrigatório, preservando o valor original e registrando auditoria |
| **MUST** | Homologar o dossiê gerando snapshot imutável com hash; exportar XLSX e JSON do snapshot |
| **SHOULD** | Classificação manual para documentos não reconhecidos |
| **SHOULD** | De-para simplificado rubrica da folha → conta contábil, além da conciliação por totais |
| **SHOULD** | Painel do dossiê com pendências: competências faltantes, divergências, arquivos com erro |
| **COULD** | Exibir recorte visual (imagem) da região do PDF de onde veio o valor |

---

## Success Criteria

- [ ] Os 6 PDFs de `docs/Amostras/` são classificados no tipo correto, com CNPJ 37.704.456/0001-42 e competência correta (6/6).
- [ ] Completude de 100% das linhas nas amostras: todas as rubricas da folha, contas do balancete e da DRE e tributos por atividade do PGDAS-D são extraídos, e todos os totais internos dos documentos fecham a partir das linhas extraídas.
- [ ] A conciliação de ago/2026 reproduz os valores de referência com diferença ≤ R$ 1,00: receita 203.180,77; DAS 23.430,47; INSS 2.963,53; FGTS 2.706,49; proventos 34.212,13; DAS de jul/2026 38.975,46 = saldo anterior de Simples Nacional a Recolher.
- [ ] 100% dos valores extraídos têm arquivo, página e bbox de origem.
- [ ] Reprocessar o mesmo arquivo gera o mesmo conjunto de valores (mesmo hash de resultado) e não duplica registros.
- [ ] Um dossiê de 6 PDFs (3 PGDAS-D + folha + DRE + balancete) chega a "pronto para revisão" em ≤ 5 min, contados a partir do último upload.
- [ ] 0 acessos entre escritórios nos testes de RLS: um usuário do escritório A recebe zero linhas do escritório B em todas as tabelas e objetos do Storage.
- [ ] 100% dos ajustes manuais e das homologações têm autor, data/hora, valor anterior/novo e motivo no log de auditoria.
- [ ] O dossiê homologado exporta XLSX e JSON contendo o hash do snapshot, e o snapshot não pode ser alterado depois de homologado.
- [ ] `npm run verify` termina com exit 0.

---

## Acceptance Tests

| ID | Pattern | Criterion (EARS) | Gate (`kind`) |
|---|---|---|---|
| AT-001 | Event-driven | **When** o analista envia um PDF do PGDAS-D ao dossiê, the system **shall** classificá-lo como `PGDAS_D`, registrar CNPJ, período de apuração e SHA-256 e enfileirar a extração | test |
| AT-002 | Event-driven | **When** o worker processa o PGDAS-D de 08/2026 da amostra, the system **shall** extrair RPA 203.180,77, RBT12, receitas brutas anteriores por competência, receita por atividade e tributos (IRPJ, CSLL, COFINS, PIS, INSS/CPP, ICMS, IPI, ISS) com total 23.430,47 | test |
| AT-003 | Event-driven | **When** o worker processa o Resumo Geral da Folha Alterdata da amostra, the system **shall** extrair todas as rubricas (código, descrição, ativos, demitidos, afastados, total), os totais de adicionais (34.212,13), descontos (4.361,13) e líquido (29.851,00), o nº de funcionários e os valores de GPS/FGTS/IRRF | test |
| AT-004 | Event-driven | **When** o worker processa a DRE Alterdata da amostra, the system **shall** extrair todas as contas com classificação e valor com natureza D/C, e o resultado 126.353,14 | test |
| AT-005 | Event-driven | **When** o worker processa o Balancete Analítico Alterdata da amostra, the system **shall** extrair todas as contas com código, saldo anterior, débito, crédito e saldo atual com natureza D/C | test |
| AT-006 | Ubiquitous | The system **shall** gravar cada valor extraído com arquivo, página, bbox, método de extração e versão do parser | test |
| AT-007 | Event-driven | **When** a extração de um documento termina, the system **shall** executar as validações internas (PGDAS: soma das atividades = RPA e soma dos tributos = total; Folha: adicionais − descontos = líquido; DRE: contas = subtotais = resultado; Balancete: saldo anterior + débito − crédito = saldo atual por conta) e registrar cada resultado | test |
| AT-008 | Event-driven | **When** o dossiê tem PGDAS-D, Folha, DRE e Balancete da mesma competência, the system **shall** conciliar receita, DAS, INSS, FGTS e proventos e marcar como conciliado cada par com diferença ≤ tolerância | test |
| AT-009 | Unwanted | **If** uma conciliação apresenta diferença acima da tolerância configurada (padrão R$ 1,00), **then** the system **shall** bloquear a homologação até que o valor seja corrigido ou a divergência seja justificada | test |
| AT-010 | Unwanted | **If** o PDF enviado não tem camada de texto, **then** the system **shall** rejeitá-lo com a mensagem "PDF sem texto selecionável — OCR não suportado" e não criar valores extraídos | test |
| AT-011 | Unwanted | **If** um arquivo com o mesmo SHA-256 já existe no dossiê, **then** the system **shall** alertar duplicidade e não processá-lo novamente | test |
| AT-012 | Unwanted | **If** o CNPJ extraído difere do CNPJ da empresa do dossiê, **then** the system **shall** marcar o arquivo com erro bloqueante "CNPJ divergente" | test |
| AT-013 | Unwanted | **If** nenhuma âncora de cabeçalho conhecida é encontrada, **then** the system **shall** marcar o documento como "não classificado" e permitir a classificação manual | test |
| AT-014 | Unwanted | **If** o parser não encontra uma âncora de layout esperada em um documento classificado, **then** the system **shall** marcar o job como falho com "layout não reconhecido" e a versão do parser, sem gravar valores parciais | test |
| AT-015 | Unwanted | **If** o mesmo job é reexecutado após falha ou retry, **then** the system **shall** produzir o mesmo conjunto de valores sem duplicar registros | test |
| AT-016 | State-driven | **While** faltar alguma competência de um tipo de documento no período do dossiê, the system **shall** exibir o alerta de competência faltante sem bloquear a homologação | test |
| AT-017 | Event-driven | **When** o analista altera um valor extraído, the system **shall** exigir motivo, preservar o valor original e registrar autor, data/hora, valor anterior e novo em auditoria | test |
| AT-018 | Unwanted | **If** um usuário tenta ler ou gravar dados ou arquivos de outro escritório, **then** the system **shall** negar o acesso via RLS e políticas de Storage, retornando zero linhas | test |
| AT-019 | Event-driven | **When** o analista homologa um dossiê sem bloqueios, the system **shall** gerar um snapshot imutável com hash SHA-256 e registrar o evento em auditoria | test |
| AT-020 | State-driven | **While** um dossiê estiver homologado, the system **shall** rejeitar qualquer alteração de valores do snapshot | test |
| AT-021 | Event-driven | **When** o usuário exporta um dossiê homologado, the system **shall** gerar XLSX e JSON com todos os valores, origens, ajustes, resultados de conciliação e o hash do snapshot | test |
| AT-022 | Event-driven | **When** os 6 PDFs de amostra são enviados a um dossiê, the system **shall** deixá-lo "pronto para revisão" em ≤ 5 minutos, contados a partir do último upload | smoke |

---

## Clarifications

### Session 2026-09-24

- [x] (NFRs / Edge cases) Tolerância de conciliação que bloqueia a homologação → R$ 1,00 absoluto, configurável por escritório (padrão R$ 1,00); integrada em Goals, Success Criteria e AT-008/AT-009
- [x] (Done signal) Comando do Verify Gate → `npm run verify` na raiz, criado no Build, encadeando pytest do worker (casos dourados), testes de banco/RLS (`supabase test db`) e testes do web; integrado em Verify Gate
- [x] (NFRs) Definição de "dossiê padrão" para a meta de 5 min → 6 PDFs (3 PGDAS-D + folha + DRE + balancete), do último upload até "pronto para revisão"; integrada em Success Criteria e AT-022
- [x] (Scope / Data model) Regra de completude → extrair todas as linhas de cada documento, meta de 100% nas amostras, verificada pelos totais internos; integrada em Success Criteria e AT-002 a AT-007
- Varredura das 9 categorias: Scope (Clear), Data model (Clear: entidades do PRD §6.2 restritas ao escopo), UX flow (Clear: upload → revisão → conciliação → homologação → exportação), NFRs (Clear após clarificação), Integrations (Clear: Supabase; sem integração externa), Edge cases (Clear: AT-009 a AT-016), Constraints (Clear), Terminology (Clear: "competência" = mês de referência MM/AAAA; "dossiê" = empresa + período; "homologar" = congelar snapshot), Done signal (Clear após clarificação).

---

## Verify Gate

```yaml
verify_gate:
  kind: test
  cmd: "npm run verify"
  pass_when: "exit 0"
  threshold: "—"
  manual_fallback: "—"
```

---

## Out of Scope

- Motor tributário: elegibilidade e cálculo de Simples Nacional, Lucro Presumido e Lucro Real; projeção; sensibilidade; recomendação; PDF executivo.
- OCR de PDF escaneado; importação de XLSX/CSV.
- Relatórios de outros ERPs além da Alterdata; IA para classificação ou extração de layouts desconhecidos; mapeamento genérico de colunas com layout salvo.
- Razão contábil.
- Papéis Revisor, Cliente e Auditor; fluxo elaborar → revisar → aprovar → emitir.
- MFA, política de retenção configurável e antivírus no upload.
- Cadastro público de escritórios, planos e cobrança.
- Integrações com e-CAC, eSocial, EFD ou ERPs.

---

## Constraints

| Type | Constraint | Impact |
|---|---|---|
| Technical | Stack: Next.js (web) + Supabase (Auth, Postgres com RLS, Storage privado, fila) + worker Python com `pdfplumber` | Duas linguagens e um container adicional para o worker |
| Technical | Entradas limitadas a PDF com camada de texto do PGDAS-D e da Alterdata (Resumo Geral da Folha, DRE, Balancete Analítico) | Parsers determinísticos por layout; outros documentos são rejeitados ou ficam "não classificados" |
| Technical | Extração por coordenadas; `pdftotext -layout` embaralha colunas nesses PDFs | Parsers devem reconstruir linhas por posição (`top`/`x0`) |
| Technical | Processamento determinístico e reproduzível; nenhuma IA no caminho de dados | Mesmas entradas + mesma versão de parser = mesmo resultado |
| Technical | Verify Gate `npm run verify` deve existir na raiz ao fim do Build | Build precisa criar e manter esse script |
| Resource | Amostras de um único cliente; folha e contábil apenas de ago/2026 | Casos dourados limitados; ampliar no piloto |
| Other | LGPD: os PDFs contêm CPF, RG e nomes de sócios e do contador | Storage privado, logs técnicos sem dados pessoais; fixtures de teste versionadas no repositório devem ser anonimizadas |
| Timeline | N/A (não informado) | — |

---

## Technical Context

| Aspect | Value | Notes |
|---|---|---|
| **Deployment Location** | Greenfield. Proposta: `apps/web` (Next.js), `services/worker` (Python), `supabase/` (migrations, policies, testes) | Estrutura final definida no Design |
| **KB Domains** | Layout PGDAS-D (Receita Federal); relatórios Alterdata (Folha, DRE, Balancete); Simples Nacional (LC 123/2006) | `kb/` está vazio; regras vêm das amostras e do PRD |
| **IaC Impact** | New resources | Projeto Supabase (DB, Auth, Storage, filas) e hospedagem do container do worker (provedor a definir no Design) |
| **LLM Prompts** | false | Decisão do Brainstorm (Approach A): extração determinística com `pdfplumber`; IA para layouts desconhecidos foi removida via YAGNI; nenhum prompt em runtime |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|---|---|---|---|
| A-001 | Todos os escritórios do piloto usam Alterdata e geram os mesmos relatórios (Resumo Geral, DRE, Balancete Analítico) | Novos parsers ou variantes de layout seriam necessários | no |
| A-002 | Os PDFs da Alterdata gerados via "Microsoft Print To PDF" mantêm posições de coluna estáveis entre meses e empresas | Parsers baseados em coordenadas podem falhar; exigirá âncoras mais robustas | no |
| A-003 | O layout do PGDAS-D permanece o da amostra (iTextSharp, seções 2.1 a 2.8) durante o piloto | Mudança da Receita exige nova versão do parser | no |
| A-004 | A receita da conciliação é a receita líquida da conta de vendas no balancete (crédito − débito) e o valor da conta "Vendas de Produtos" na DRE | Regra de conciliação de receita teria de mudar | no (fechou na amostra de ago/2026) |
| A-005 | Plano de contas: as contas-alvo da conciliação (Vendas, Simples Nacional, INSS a Pagar, FGTS, Salários a Pagar) são identificáveis pelo código/descrição Alterdata e parametrizáveis por empresa | Seria necessário cadastro manual de contas-alvo por empresa | no |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---|---:|---|
| Problem | 3 | Dor, usuário e impacto claros e sustentados pelo PRD e pelo Brainstorm |
| Users | 3 | Analista, Administrador e consumidor do snapshot, com dores específicas |
| Goals | 3 | MUST/SHOULD/COULD priorizados e alinhados ao YAGNI |
| Success | 3 | Critérios numéricos (valores de referência, tolerância, tempo, completude, RLS) e gate executável |
| Scope | 2 | Escopo e exclusões explícitos; cobertura de layout depende de A-001/A-002 e das amostras de um único cliente |
| **Total** | **14/15** | |

Minimum to proceed: **12/15**.

---

## Open Questions

- (Não bloqueante) Onde hospedar o worker Python (Railway, Fly.io, Render ou outro) e qual plano do Supabase usar: decisão do Design.
- (Não bloqueante) Obter amostras adicionais (outros meses e clientes) e versões anonimizadas para fixtures: pode ocorrer em paralelo ao Design e Build, sem alterar os requisitos.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-24 | SDD Define by RDD | Initial version |

---

## Next Step

Execute o **SDD Design by RDD**.
