-- Valores extraídos (imutáveis para o usuário), ajustes manuais, validações internas
-- e a view de valores efetivos (original ou último ajuste).

create table public.extracted_values (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  file_id uuid not null,
  ordinal integer not null check (ordinal >= 0),
  doc_type text not null,
  competence date not null,
  section text not null,
  field_key text not null,
  label text not null,
  account_code text,
  column_name text,
  value numeric(18, 2) not null,
  nature char(1) check (nature in ('D', 'C')),
  page integer not null check (page >= 1),
  bbox numeric(10, 2)[] not null check (array_length(bbox, 1) = 4),
  parser_version text not null,
  created_at timestamptz not null default now(),
  unique (file_id, ordinal),
  foreign key (file_id, office_id) references public.source_files (id, office_id) on delete cascade,
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade
);

create index extracted_values_case_idx on public.extracted_values (case_id, competence, doc_type);

create table public.value_adjustments (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  value_id uuid not null references public.extracted_values (id) on delete restrict,
  old_value numeric(18, 2) not null,
  new_value numeric(18, 2) not null,
  reason text not null check (length(trim(reason)) >= 5),
  author uuid not null default auth.uid() references auth.users (id),
  created_at timestamptz not null default now(),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade
);

create index value_adjustments_value_idx on public.value_adjustments (value_id, created_at desc);

create table public.validations (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  file_id uuid not null,
  rule text not null,
  status text not null check (status in ('pass', 'fail')),
  expected numeric(18, 2),
  actual numeric(18, 2),
  diff numeric(18, 2),
  detail text,
  created_at timestamptz not null default now(),
  foreign key (file_id, office_id) references public.source_files (id, office_id) on delete cascade
);

create index validations_file_idx on public.validations (file_id);

-- Preenche escritório, dossiê e valor anterior a partir do valor ajustado (o cliente envia só
-- value_id, new_value e reason). Roda antes da checagem de RLS.
create or replace function public.tg_value_adjustments_fill()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v record;
begin
  select ev.office_id, ev.case_id,
         coalesce((select a.new_value from public.value_adjustments a
                    where a.value_id = ev.id order by a.created_at desc, a.id desc limit 1),
                  ev.value) as current_value
    into v
    from public.extracted_values ev
   where ev.id = new.value_id;
  if not found then
    raise exception 'Valor extraído não encontrado' using errcode = 'P0002';
  end if;
  new.office_id := v.office_id;
  new.case_id := v.case_id;
  new.old_value := v.current_value;
  new.author := coalesce(auth.uid(), new.author);
  new.created_at := now();
  return new;
end;
$$;

create trigger value_adjustments_fill
  before insert on public.value_adjustments
  for each row execute function public.tg_value_adjustments_fill();

-- Ajuste → reconciliação do dossiê.
create or replace function public.tg_value_adjustments_reconcile()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.enqueue_job(
    new.office_id, 'reconcile',
    jsonb_build_object('case_id', new.case_id),
    'reconcile:' || new.case_id || ':adj:' || new.id
  );
  return new;
end;
$$;

create trigger value_adjustments_reconcile
  after insert on public.value_adjustments
  for each row execute function public.tg_value_adjustments_reconcile();

create view public.effective_values
with (security_invoker = true) as
select
  ev.*,
  coalesce(la.new_value, ev.value) as effective_value,
  (la.id is not null) as adjusted,
  la.reason as last_reason,
  la.created_at as adjusted_at
from public.extracted_values ev
left join lateral (
  select a.id, a.new_value, a.reason, a.created_at
    from public.value_adjustments a
   where a.value_id = ev.id
   order by a.created_at desc, a.id desc
   limit 1
) la on true;

alter table public.extracted_values enable row level security;
alter table public.value_adjustments enable row level security;
alter table public.validations enable row level security;

revoke all on table public.extracted_values from anon, authenticated;
revoke all on table public.value_adjustments from anon, authenticated;
revoke all on table public.validations from anon, authenticated;
revoke all on table public.effective_values from anon, authenticated;
-- extracted_values: somente leitura para o usuário (sem UPDATE/DELETE).
grant select on table public.extracted_values to authenticated;
grant select, insert on table public.value_adjustments to authenticated;
grant select on table public.validations to authenticated;
grant select on table public.effective_values to authenticated;

create policy extracted_values_select on public.extracted_values
  for select to authenticated using (public.is_member(office_id));
create policy value_adjustments_select on public.value_adjustments
  for select to authenticated using (public.is_member(office_id));
create policy value_adjustments_insert on public.value_adjustments
  for insert to authenticated with check (public.is_member(office_id) and author = auth.uid());
create policy validations_select on public.validations
  for select to authenticated using (public.is_member(office_id));
