# Planejamento Tributário — Importação e Conciliação (ciclo 1)

Aplicativo web SaaS multi-escritório que importa PDFs do **PGDAS-D** e dos relatórios **Alterdata**
(Resumo Geral da Folha, DRE e Balancete Analítico), extrai todas as linhas com página e posição de
origem, concilia as fontes por competência (regras R1–R6), permite revisão com ajustes justificados e
**homologa** um snapshot imutável (SHA-256) exportável em JSON e XLSX.

Especificação: [`sdd/`](sdd/) (Brainstorm → Define → Design → Build). Base de conhecimento: [`kb/`](kb/).

## Arquitetura

| Parte | Pasta | Tecnologia |
|---|---|---|
| Site | `apps/web` | Next.js 16 (App Router), TypeScript, Tailwind v4, `@supabase/ssr` |
| Banco, Auth, Storage | `supabase/` | Postgres 17 com RLS por escritório, Storage privado, pgTAP |
| Worker | `services/worker` | Python 3.12+, `pdfplumber`, `psycopg`, `openpyxl` (container Docker) |

Fluxo: upload direto do navegador ao Storage → `source_files` → fila `jobs` → worker (classifica,
extrai, valida, concilia) → revisão/ajuste → `homologate_case()` → snapshot → exportação.

## Pré-requisitos

- Node.js 20+ e npm
- Python 3.12+
- **Docker Desktop em execução** (o Supabase local roda em containers)
- Supabase CLI: instalada pelo `npm install` (devDependency). Use sempre `npx supabase …` — não é preciso instalação global.

## Configuração local

```bash
npm install
python -m pip install -e "services/worker[dev]"
npm run db:start
```

`npm run db:start` aplica as migrations e o `supabase/seed.sql` (dados fictícios). Depois:

1. Rode `npx supabase status` e copie `API_URL`, `ANON_KEY` e `SERVICE_ROLE_KEY`.
2. Crie `apps/web/.env.local` com `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` e `SUPABASE_SERVICE_ROLE_KEY` (modelo em `.env.example`).
3. Para o worker, exporte `DATABASE_URL`, `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`.

Usuários do seed (senha `senha-local-123`): `admin.a@example.com` (admin do Escritório A),
`analista.a@example.com` (analista do A), `analista.b@example.com` (analista do B).

```bash
npm run dev:web
npm run dev:worker
```

Site em http://localhost:3000; e-mails de convite locais em http://127.0.0.1:54324 (Mailpit).

## Verify Gate

```bash
npm run verify
```

Executa, e só passa (exit 0) se tudo passar:

1. checagem das amostras em `SAMPLES_DIR`, do Docker Engine e do Supabase local;
2. `pytest` do worker (golden das 6 amostras, validações, conciliação, pipeline com Postgres, desempenho ≤ 5 min);
3. `npx supabase test db` (pgTAP: isolamento RLS entre escritórios e homologação);
4. typecheck e vitest do site.

### Amostras e LGPD

Os PDFs reais contêm CPF, RG e nomes, por isso **ficam fora do Git** (`docs/Amostras/` está no
`.gitignore`). Os testes leem os PDFs de `SAMPLES_DIR` (padrão `docs/Amostras`) e comparam com
`services/worker/tests/golden/*.json`, que contêm só campos, códigos e valores, sem dados pessoais.
Logs do worker registram apenas IDs e códigos de erro.

## Deploy (fora deste ciclo)

- Worker: `docker build -t planejamento-worker services/worker`, configurado só por variáveis de ambiente.
- Site: `npm run build --workspace apps/web` e `next start` em qualquer host Node.
- Banco: `npx supabase link` + `npx supabase db push` para o projeto remoto.
