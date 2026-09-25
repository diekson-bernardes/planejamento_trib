-- Ciclo 2 — motor tributário: premissas, simulações e memória de cálculo.
-- Leitura por membros do escritório (RLS); escrita de usuários só pelas RPCs; gravação de resultados pelo worker.

alter table public.jobs drop constraint jobs_kind_check;
alter table public.jobs add constraint jobs_kind_check check (kind in (
  'extract', 'reconcile', 'export_xlsx', 'suggest_assumptions', 'calculate', 'export_simulation'
));

-- ---------------------------------------------------------------- premissas
create table public.assumptions (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  key text not null,
  scope text not null,
  grp text not null,
  label text not null,
  value_type text not null,
  choices jsonb,
  suggested_value jsonb,
  suggested_origin jsonb not null default '{}'::jsonb,
  value jsonb,
  status text not null default 'pending' check (status in ('pending', 'confirmed')),
  justification text,
  confirmed_by uuid references auth.users (id),
  confirmed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (case_id, key, scope),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade
);

create index assumptions_case_idx on public.assumptions (case_id, grp);

-- ---------------------------------------------------------------- simulações
create table public.simulations (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  snapshot_id uuid not null references public.snapshots (id),
  snapshot_sha256 char(64) not null,
  assumptions_hash char(64) not null,
  rules_version text not null,
  rules_hash char(64) not null,
  status text not null check (status in ('done', 'failed')),
  result_hash char(64),
  result jsonb not null default '{}'::jsonb,
  error_code text,
  error_message text,
  requested_by uuid references auth.users (id),
  duration_ms integer,
  created_at timestamptz not null default now(),
  unique (case_id, snapshot_sha256, assumptions_hash, rules_hash),
  unique (id, office_id),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade
);

create index simulations_case_idx on public.simulations (case_id, created_at desc);

create table public.simulation_lines (
  id bigint generated always as identity primary key,
  office_id uuid not null references public.offices (id) on delete cascade,
  simulation_id uuid not null,
  ordinal integer not null,
  regime text not null check (regime in ('SIMPLES', 'PRESUMIDO', 'REAL')),
  period text not null,
  tax text not null,
  kind text not null check (kind in ('tributo', 'reclassificacao', 'informativo')),
  base numeric(18, 2) not null,
  rate numeric(18, 10) not null,
  amount numeric(18, 2) not null,
  formula text not null,
  rule_ref text not null,
  origin jsonb not null default '{}'::jsonb,
  activity text,
  partial boolean not null default false,
  verified boolean not null default true,
  unique (simulation_id, ordinal),
  foreign key (simulation_id, office_id) references public.simulations (id, office_id) on delete cascade
);

create index simulation_lines_sim_idx on public.simulation_lines (simulation_id, regime, period);

-- Simulação e memória são imutáveis após gravadas.
create trigger simulations_append_only
  before update or delete on public.simulations
  for each row execute function public.tg_append_only();
create trigger simulation_lines_append_only
  before update or delete on public.simulation_lines
  for each row execute function public.tg_append_only();

-- ---------------------------------------------------------------- RLS
alter table public.assumptions enable row level security;
alter table public.simulations enable row level security;
alter table public.simulation_lines enable row level security;

revoke all on table public.assumptions from anon, authenticated;
revoke all on table public.simulations from anon, authenticated;
revoke all on table public.simulation_lines from anon, authenticated;
grant select on table public.assumptions to authenticated;
grant select on table public.simulations to authenticated;
grant select on table public.simulation_lines to authenticated;

create policy assumptions_select on public.assumptions
  for select to authenticated using (public.is_member(office_id));
create policy simulations_select on public.simulations
  for select to authenticated using (public.is_member(office_id));
create policy simulation_lines_select on public.simulation_lines
  for select to authenticated using (public.is_member(office_id));

-- ---------------------------------------------------------------- RPCs
-- Dossiê homologado do escritório do usuário (ou erro).
create or replace function public.planning_case(p_case_id uuid)
returns public.tax_cases
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
begin
  select * into v from public.tax_cases where id = p_case_id;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Dossiê não encontrado' using errcode = 'P0002';
  end if;
  if v.status <> 'homologated' then
    raise exception 'Planejamento exige dossiê homologado' using errcode = 'P0001';
  end if;
  return v;
end;
$$;

create or replace function public.request_planning(p_case_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
  v_sha text;
begin
  v := public.planning_case(p_case_id);
  select sha256 into v_sha from public.snapshots where case_id = p_case_id;
  -- chave nova a cada pedido: regenerar após troca de regras ou de perfil (o upsert do worker é idempotente)
  perform public.enqueue_job(v.office_id, 'suggest_assumptions',
    jsonb_build_object('case_id', p_case_id), 'suggest:' || p_case_id || ':' || v_sha || ':' || txid_current());
  perform public.write_audit(v.office_id, 'planning.requested', 'tax_cases', p_case_id, null, null);
end;
$$;

-- Tipo do valor conforme value_type: o worker lê estes valores sem outra validação.
create or replace function public.assumption_value_ok(p_type text, p_choices jsonb, p_value jsonb)
returns boolean
language sql
immutable
set search_path = public
as $$
  select case p_type
    when 'decimal' then jsonb_typeof(p_value) in ('string', 'number')
                        and (p_value #>> '{}') ~ '^-?[0-9]+(\.[0-9]+)?$'
    when 'percent' then jsonb_typeof(p_value) in ('string', 'number')
                        and case when (p_value #>> '{}') ~ '^[0-9]+(\.[0-9]+)?$'
                                 then (p_value #>> '{}')::numeric <= 1 else false end
    when 'boolean' then jsonb_typeof(p_value) = 'boolean'
    when 'choice' then jsonb_typeof(p_value) = 'string' and coalesce(p_choices @> jsonb_build_array(p_value), false)
    when 'taxes' then jsonb_typeof(p_value) = 'array'
                      and not exists (select 1 from jsonb_array_elements(p_value) e
                                       where jsonb_typeof(e) <> 'string'
                                          or (e #>> '{}') not in ('icms', 'iss', 'pis', 'cofins', 'ipi'))
    when 'profile' then jsonb_typeof(p_value) = 'object'
                        and (p_value ->> 'anexo') in ('I', 'II', 'III', 'IV', 'V')
                        and exists (select 1 from jsonb_array_elements(coalesce(p_choices, '[]')) c
                                     where c -> 'presumido' ? (p_value ->> 'presumido'))
                        and not exists (select 1 from unnest(array['cumulativo_no_real', 'fator_r', 'exportacao']) k
                                         where p_value ? k and jsonb_typeof(p_value -> k) <> 'boolean')
    else false
  end;
$$;

create or replace function public.confirm_assumption(p_id uuid, p_value jsonb, p_justification text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.assumptions%rowtype;
begin
  select * into v from public.assumptions where id = p_id for update;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Premissa não encontrada' using errcode = 'P0002';
  end if;
  if p_value is null or p_value = 'null'::jsonb then
    raise exception 'Informe um valor para a premissa' using errcode = 'P0001';
  end if;
  if not public.assumption_value_ok(v.value_type, v.choices, p_value) then
    raise exception 'Valor inválido para a premissa (%)', v.value_type using errcode = 'P0001';
  end if;
  if p_value is distinct from v.suggested_value
     and (p_justification is null or length(trim(p_justification)) < 5) then
    raise exception 'Justificativa obrigatória (mín. 5 caracteres) ao alterar o valor sugerido' using errcode = 'P0001';
  end if;
  update public.assumptions
     set value = p_value, status = 'confirmed', justification = nullif(trim(coalesce(p_justification, '')), ''),
         confirmed_by = auth.uid(), confirmed_at = now(), updated_at = now()
   where id = p_id;
  perform public.write_audit(v.office_id, 'assumption.confirmed', 'assumptions', p_id,
    jsonb_build_object('suggested', v.suggested_value, 'previous', v.value),
    jsonb_build_object('value', p_value, 'justification', p_justification, 'key', v.key, 'scope', v.scope));
end;
$$;

create or replace function public.request_calculation(p_case_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
  v_pending text[];
  v_total integer;
begin
  v := public.planning_case(p_case_id);
  select count(*), array_agg(label order by grp, key, scope) filter (where status = 'pending')
    into v_total, v_pending
    from public.assumptions where case_id = p_case_id;
  if v_total = 0 then
    raise exception 'Gere as premissas do planejamento antes de calcular' using errcode = 'P0001';
  end if;
  if array_length(v_pending, 1) > 0 then
    raise exception 'Premissas pendentes de confirmação: %', array_to_string(v_pending, '; ') using errcode = 'P0001';
  end if;
  -- chave nova a cada pedido; o worker não duplica simulação com os mesmos hashes
  perform public.enqueue_job(v.office_id, 'calculate',
    jsonb_build_object('case_id', p_case_id, 'requested_by', auth.uid()),
    'calculate:' || p_case_id || ':' || txid_current());
  perform public.write_audit(v.office_id, 'calculation.requested', 'tax_cases', p_case_id, null, null);
end;
$$;

create or replace function public.request_simulation_export(p_simulation_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.simulations%rowtype;
begin
  select * into v from public.simulations where id = p_simulation_id;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Simulação não encontrada' using errcode = 'P0002';
  end if;
  if v.status <> 'done' then
    raise exception 'Simulação sem resultado para exportar' using errcode = 'P0001';
  end if;
  update public.jobs
     set status = 'queued', attempts = 0, run_after = now(), last_error = null, finished_at = null, locked_at = null
   where idempotency_key = 'export_simulation:' || p_simulation_id and status = 'failed';
  if found then
    return;
  end if;
  perform public.enqueue_job(v.office_id, 'export_simulation',
    jsonb_build_object('case_id', v.case_id, 'simulation_id', p_simulation_id), 'export_simulation:' || p_simulation_id);
end;
$$;

revoke all on function public.planning_case(uuid) from public, anon, authenticated;
revoke all on function public.request_planning(uuid) from public, anon;
revoke all on function public.confirm_assumption(uuid, jsonb, text) from public, anon;
revoke all on function public.request_calculation(uuid) from public, anon;
revoke all on function public.request_simulation_export(uuid) from public, anon;
grant execute on function public.request_planning(uuid) to authenticated;
grant execute on function public.confirm_assumption(uuid, jsonb, text) to authenticated;
grant execute on function public.request_calculation(uuid) to authenticated;
grant execute on function public.request_simulation_export(uuid) to authenticated;

-- ---------------------------------------------------------------- Storage: usuários não gravam memória exportada
drop policy if exists documents_insert on storage.objects;
create policy documents_insert on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'documents'
    and public.is_member(public.storage_path_office(name))
    and name not like '%/exports/%'
    and name not like '%/simulations/%'
  );
