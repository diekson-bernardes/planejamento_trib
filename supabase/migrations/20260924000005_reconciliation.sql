-- Resultados de conciliação entre fontes (R1–R6) por competência.
-- O usuário só pode escrever a justificativa; o restante é gravado pelo worker.

create table public.reconciliations (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  competence date not null,
  rule text not null check (rule in ('R1', 'R2', 'R3', 'R4', 'R5', 'R6')),
  description text not null,
  left_label text not null,
  left_value numeric(18, 2),
  right_label text not null,
  right_value numeric(18, 2),
  diff numeric(18, 2),
  tolerance numeric(18, 2) not null,
  status text not null check (status in ('ok', 'divergent', 'missing_source')),
  details jsonb not null default '{}'::jsonb,
  justification text,
  justified_by uuid references auth.users (id),
  justified_at timestamptz,
  updated_at timestamptz not null default now(),
  unique (case_id, competence, rule),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade
);

-- Justificativa exige texto mínimo e registra autor e data.
create or replace function public.tg_reconciliations_justify()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.justification is distinct from old.justification and auth.uid() is not null then
    if new.justification is null or length(trim(new.justification)) < 5 then
      raise exception 'Justificativa deve ter ao menos 5 caracteres' using errcode = 'P0001';
    end if;
    new.justified_by := auth.uid();
    new.justified_at := now();
  end if;
  return new;
end;
$$;

create trigger reconciliations_justify
  before update on public.reconciliations
  for each row execute function public.tg_reconciliations_justify();

alter table public.reconciliations enable row level security;

revoke all on table public.reconciliations from anon, authenticated;
grant select on table public.reconciliations to authenticated;
grant update (justification) on table public.reconciliations to authenticated;

create policy reconciliations_select on public.reconciliations
  for select to authenticated using (public.is_member(office_id));
create policy reconciliations_update on public.reconciliations
  for update to authenticated using (public.is_member(office_id)) with check (public.is_member(office_id));
