-- Empresas, dossiês (tax_cases) e mapeamento de contas-alvo da conciliação.
-- FKs compostas (id, office_id) impedem referências entre escritórios diferentes.

create table public.companies (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  cnpj char(14) not null check (cnpj ~ '^[0-9]{14}$'),
  legal_name text not null check (length(trim(legal_name)) > 0),
  created_at timestamptz not null default now(),
  unique (office_id, cnpj),
  unique (id, office_id)
);

create table public.tax_cases (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  company_id uuid not null,
  period_start date not null,
  period_end date not null,
  status text not null default 'draft'
    check (status in ('draft', 'processing', 'review', 'homologated')),
  created_by uuid default auth.uid() references auth.users (id),
  created_at timestamptz not null default now(),
  check (period_end >= period_start),
  unique (id, office_id),
  foreign key (company_id, office_id) references public.companies (id, office_id)
);

create index tax_cases_office_idx on public.tax_cases (office_id);

create table public.account_mappings (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  company_id uuid,
  target text not null check (target in (
    'vendas', 'simples_despesa', 'simples_a_recolher',
    'inss_a_pagar', 'fgts_a_pagar', 'salarios_a_pagar'
  )),
  doc_type text not null check (doc_type in ('DRE_ALTERDATA', 'BALANCETE_ALTERDATA')),
  account_code text not null check (length(trim(account_code)) > 0),
  created_at timestamptz not null default now(),
  foreign key (company_id, office_id) references public.companies (id, office_id) on delete cascade,
  unique nulls not distinct (office_id, company_id, target, doc_type)
);

alter table public.companies enable row level security;
alter table public.tax_cases enable row level security;
alter table public.account_mappings enable row level security;

revoke all on table public.companies from anon, authenticated;
revoke all on table public.tax_cases from anon, authenticated;
revoke all on table public.account_mappings from anon, authenticated;

grant select, insert on table public.companies to authenticated;
grant update (legal_name) on table public.companies to authenticated;
-- status do caso só muda pelo worker (service role) ou por homologate_case().
grant select, insert on table public.tax_cases to authenticated;
grant update (period_start, period_end) on table public.tax_cases to authenticated;
grant select, insert, update, delete on table public.account_mappings to authenticated;

create policy companies_select on public.companies
  for select to authenticated using (public.is_member(office_id));
create policy companies_insert on public.companies
  for insert to authenticated with check (public.is_member(office_id));
create policy companies_update on public.companies
  for update to authenticated using (public.is_member(office_id)) with check (public.is_member(office_id));

create policy tax_cases_select on public.tax_cases
  for select to authenticated using (public.is_member(office_id));
create policy tax_cases_insert on public.tax_cases
  for insert to authenticated with check (public.is_member(office_id) and status = 'draft');
create policy tax_cases_update on public.tax_cases
  for update to authenticated
  using (public.is_member(office_id) and status <> 'homologated')
  with check (public.is_member(office_id));

create policy account_mappings_select on public.account_mappings
  for select to authenticated using (public.is_member(office_id));
create policy account_mappings_write on public.account_mappings
  for all to authenticated using (public.is_admin(office_id)) with check (public.is_admin(office_id));
