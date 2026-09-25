-- Ciclo 3 — decisão tributária: projeção do exercício, sensibilidade, recomendação com aprovação do
-- responsável técnico e PDF executivo imutável. Leitura por membros (RLS); escrita de usuários só por RPC;
-- projeções e PDFs gravados pelo worker.

alter table public.jobs drop constraint jobs_kind_check;
alter table public.jobs add constraint jobs_kind_check check (kind in (
  'extract', 'reconcile', 'export_xlsx', 'suggest_assumptions', 'calculate', 'export_simulation',
  'project', 'emit_report'
));

-- ---------------------------------------------------------------- premissas: tipo "ratio" (fração com sinal)
-- Margem projetada pode ser negativa (prejuízo): fração entre −1 e 1.
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
    when 'ratio' then jsonb_typeof(p_value) in ('string', 'number')
                      and case when (p_value #>> '{}') ~ '^-?[0-9]+(\.[0-9]+)?$'
                               then abs((p_value #>> '{}')::numeric) <= 1 else false end
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

-- ---------------------------------------------------------------- responsável técnico e limiar
alter table public.office_members
  add column is_technical_responsible boolean not null default false,
  add column professional_name text,
  add column crc text,
  add constraint office_members_technical_identified check (
    not is_technical_responsible
    or (length(trim(coalesce(professional_name, ''))) >= 3 and length(trim(coalesce(crc, ''))) >= 4)
  );

alter table public.offices add constraint offices_decision_threshold_valid check (
  not (settings ? 'decision_threshold')
  or ((settings ->> 'decision_threshold')::numeric > 0 and (settings ->> 'decision_threshold')::numeric < 1)
);

create or replace function public.is_technical_responsible(p_office uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.office_members
    where office_id = p_office and user_id = auth.uid() and is_technical_responsible
  );
$$;

create or replace function public.decision_threshold(p_office uuid)
returns numeric
language sql
stable
security definer
set search_path = public
as $$
  select coalesce((settings ->> 'decision_threshold')::numeric, 0.05) from public.offices
   where id = p_office and public.is_member(p_office);
$$;

create or replace function public.set_technical_responsible(
  p_office uuid, p_user uuid, p_flag boolean, p_name text, p_crc text
) returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.office_members%rowtype;
begin
  if not public.is_admin(p_office) then
    raise exception 'Acesso restrito ao administrador do escritório' using errcode = '42501';
  end if;
  select * into v from public.office_members where office_id = p_office and user_id = p_user for update;
  if not found then
    raise exception 'Membro não encontrado' using errcode = 'P0002';
  end if;
  if p_flag and (length(trim(coalesce(p_name, ''))) < 3 or length(trim(coalesce(p_crc, ''))) < 4) then
    raise exception 'Informe nome profissional e CRC do responsável técnico' using errcode = 'P0001';
  end if;
  update public.office_members
     set is_technical_responsible = p_flag,
         professional_name = case when p_flag then trim(p_name) else professional_name end,
         crc = case when p_flag then upper(trim(p_crc)) else crc end
   where office_id = p_office and user_id = p_user;
  perform public.write_audit(p_office, 'member.technical_responsible', 'office_members', p_user,
    jsonb_build_object('flag', v.is_technical_responsible, 'name', v.professional_name, 'crc', v.crc),
    jsonb_build_object('flag', p_flag, 'name', trim(p_name), 'crc', upper(trim(p_crc))));
end;
$$;

create or replace function public.set_decision_threshold(p_office uuid, p_threshold numeric)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_before jsonb;
begin
  if not public.is_admin(p_office) then
    raise exception 'Acesso restrito ao administrador do escritório' using errcode = '42501';
  end if;
  if p_threshold is null or p_threshold <= 0 or p_threshold >= 1 then
    raise exception 'Limiar deve estar entre 0 e 1 (fração do custo do regime vencedor)' using errcode = 'P0001';
  end if;
  select settings into v_before from public.offices where id = p_office for update;
  update public.offices set settings = settings || jsonb_build_object('decision_threshold', p_threshold)
   where id = p_office;
  perform public.write_audit(p_office, 'office.decision_threshold', 'offices', p_office,
    jsonb_build_object('decision_threshold', v_before -> 'decision_threshold'),
    jsonb_build_object('decision_threshold', p_threshold));
end;
$$;

-- ---------------------------------------------------------------- projeções (imutáveis)
create table public.projections (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  snapshot_id uuid not null references public.snapshots (id),
  snapshot_sha256 char(64) not null,
  assumptions_hash char(64) not null,
  rules_version text not null,
  rules_hash char(64) not null,
  decision_version text not null,
  decision_hash char(64) not null,
  threshold numeric(6, 4) not null,
  year integer not null,
  status text not null check (status in ('done', 'failed')),
  result jsonb not null default '{}'::jsonb,
  sensitivity jsonb not null default '[]'::jsonb,
  recommendation jsonb not null default '{}'::jsonb,
  assumptions jsonb not null default '[]'::jsonb,
  result_hash char(64),
  error_code text,
  error_message text,
  engine_runs integer,
  duration_ms integer,
  requested_by uuid references auth.users (id),
  created_at timestamptz not null default now(),
  unique (case_id, snapshot_sha256, assumptions_hash, rules_hash, decision_hash, threshold),
  unique (id, office_id),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade
);

create index projections_case_idx on public.projections (case_id, created_at desc);

create table public.projection_lines (
  id bigint generated always as identity primary key,
  office_id uuid not null references public.offices (id) on delete cascade,
  projection_id uuid not null,
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
  unique (projection_id, ordinal),
  foreign key (projection_id, office_id) references public.projections (id, office_id) on delete cascade
);

create index projection_lines_proj_idx on public.projection_lines (projection_id, regime, period);

create trigger projections_append_only
  before update or delete on public.projections
  for each row execute function public.tg_append_only();
create trigger projection_lines_append_only
  before update or delete on public.projection_lines
  for each row execute function public.tg_append_only();

-- ---------------------------------------------------------------- recomendação (estado do fluxo)
create table public.recommendations (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  projection_id uuid not null,
  status text not null default 'rascunho'
    check (status in ('rascunho', 'em_revisao', 'aprovada', 'emitida')),
  computed_status text not null check (computed_status in ('recomendado', 'inconclusivo', 'bloqueado')),
  elaborated_by uuid references auth.users (id),
  approved_by uuid references auth.users (id),
  approved_at timestamptz,
  pdf_path text,
  pdf_sha256 char(64),
  emitted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (projection_id),
  unique (id, office_id),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade,
  foreign key (projection_id, office_id) references public.projections (id, office_id) on delete cascade
);

create index recommendations_case_idx on public.recommendations (case_id, created_at desc);

create table public.recommendation_events (
  id bigint generated always as identity primary key,
  office_id uuid not null references public.offices (id) on delete cascade,
  recommendation_id uuid not null,
  event text not null check (event in ('created', 'submitted', 'returned', 'approved', 'emission_requested',
                                       'emitted', 'reset_by_assumption')),
  actor uuid references auth.users (id),
  comment text,
  created_at timestamptz not null default now(),
  foreign key (recommendation_id, office_id) references public.recommendations (id, office_id) on delete cascade
);

create index recommendation_events_rec_idx on public.recommendation_events (recommendation_id, created_at);

create trigger recommendation_events_append_only
  before update or delete on public.recommendation_events
  for each row execute function public.tg_append_only();

-- Recomendação emitida é imutável (o PDF emitido e seu hash não mudam).
create or replace function public.tg_recommendation_emitted_immutable()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'DELETE' then
    if old.status = 'emitida' then
      raise exception 'Recomendação emitida é imutável' using errcode = 'P0001';
    end if;
    return old;
  end if;
  if old.status = 'emitida' then
    raise exception 'Recomendação emitida é imutável' using errcode = 'P0001';
  end if;
  new.updated_at := now();
  return new;
end;
$$;

create trigger recommendations_emitted_immutable
  before update or delete on public.recommendations
  for each row execute function public.tg_recommendation_emitted_immutable();

-- Premissa confirmada, alterada, voltada a pendente (regeneração) ou removida: recomendações do caso em revisão
-- ou aprovadas voltam a rascunho (a emitida não muda).
create or replace function public.tg_assumption_resets_recommendations()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  r record;
  v_case uuid;
  v_label text;
begin
  if tg_op = 'DELETE' then
    if old.status <> 'confirmed' then
      return old;
    end if;
    v_case := old.case_id;
    v_label := old.key || ' ' || old.scope || ' (removida)';
  elsif (new.status = 'confirmed' and (new.value is distinct from old.value or old.status <> 'confirmed'))
        or (new.status = 'pending' and old.status = 'confirmed') then
    v_case := new.case_id;
    v_label := new.key || ' ' || new.scope;
  else
    return new;
  end if;
  for r in
    update public.recommendations set status = 'rascunho', approved_by = null, approved_at = null
     where case_id = v_case and status in ('em_revisao', 'aprovada')
    returning id, office_id
  loop
    insert into public.recommendation_events (office_id, recommendation_id, event, actor, comment)
    values (r.office_id, r.id, 'reset_by_assumption', auth.uid(), v_label);
  end loop;
  return coalesce(new, old);
end;
$$;

create trigger assumptions_reset_recommendations
  after update or delete on public.assumptions
  for each row execute function public.tg_assumption_resets_recommendations();

-- ---------------------------------------------------------------- RLS
alter table public.projections enable row level security;
alter table public.projection_lines enable row level security;
alter table public.recommendations enable row level security;
alter table public.recommendation_events enable row level security;

revoke all on table public.projections from anon, authenticated;
revoke all on table public.projection_lines from anon, authenticated;
revoke all on table public.recommendations from anon, authenticated;
revoke all on table public.recommendation_events from anon, authenticated;
grant select on table public.projections to authenticated;
grant select on table public.projection_lines to authenticated;
grant select on table public.recommendations to authenticated;
grant select on table public.recommendation_events to authenticated;

create policy projections_select on public.projections
  for select to authenticated using (public.is_member(office_id));
create policy projection_lines_select on public.projection_lines
  for select to authenticated using (public.is_member(office_id));
create policy recommendations_select on public.recommendations
  for select to authenticated using (public.is_member(office_id));
create policy recommendation_events_select on public.recommendation_events
  for select to authenticated using (public.is_member(office_id));

-- ---------------------------------------------------------------- RPCs do fluxo
-- Projeção do exercício. Premissas pendentes não impedem o pedido: a recomendação sai "bloqueado" (prévia).
create or replace function public.request_projection(p_case_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
begin
  v := public.planning_case(p_case_id);
  if not exists (select 1 from public.assumptions where case_id = p_case_id) then
    raise exception 'Gere as premissas do planejamento antes de projetar' using errcode = 'P0001';
  end if;
  perform public.enqueue_job(v.office_id, 'project',
    jsonb_build_object('case_id', p_case_id, 'requested_by', auth.uid()),
    'project:' || p_case_id || ':' || txid_current());
  perform public.write_audit(v.office_id, 'projection.requested', 'tax_cases', p_case_id, null, null);
end;
$$;

create or replace function public.recommendation_for_update(p_id uuid)
returns public.recommendations
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.recommendations%rowtype;
begin
  select * into v from public.recommendations where id = p_id for update;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Recomendação não encontrada' using errcode = 'P0002';
  end if;
  return v;
end;
$$;

create or replace function public.submit_recommendation(p_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.recommendations%rowtype;
begin
  v := public.recommendation_for_update(p_id);
  if v.status <> 'rascunho' then
    raise exception 'Somente recomendação em rascunho pode ser enviada para revisão' using errcode = 'P0001';
  end if;
  if v.computed_status = 'bloqueado' then
    raise exception 'Recomendação bloqueada por dado crítico ausente: resolva as pendências e projete de novo'
      using errcode = 'P0001';
  end if;
  if exists (select 1 from public.recommendations
              where case_id = v.case_id and id <> v.id and status in ('em_revisao', 'aprovada')) then
    raise exception 'Já existe recomendação deste dossiê em revisão ou aprovada' using errcode = 'P0001';
  end if;
  update public.recommendations set status = 'em_revisao' where id = p_id;
  insert into public.recommendation_events (office_id, recommendation_id, event, actor)
  values (v.office_id, p_id, 'submitted', auth.uid());
end;
$$;

create or replace function public.approve_recommendation(p_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.recommendations%rowtype;
begin
  v := public.recommendation_for_update(p_id);
  if not public.is_technical_responsible(v.office_id) then
    raise exception 'Somente o responsável técnico aprova' using errcode = '42501';
  end if;
  if v.elaborated_by = auth.uid() then
    raise exception 'Quem elaborou não pode aprovar a própria recomendação' using errcode = '42501';
  end if;
  if v.status <> 'em_revisao' then
    raise exception 'Recomendação não está em revisão' using errcode = 'P0001';
  end if;
  update public.recommendations set status = 'aprovada', approved_by = auth.uid(), approved_at = now()
   where id = p_id;
  insert into public.recommendation_events (office_id, recommendation_id, event, actor)
  values (v.office_id, p_id, 'approved', auth.uid());
  perform public.write_audit(v.office_id, 'recommendation.approved', 'recommendations', p_id, null,
    jsonb_build_object('projection_id', v.projection_id));
end;
$$;

create or replace function public.return_recommendation(p_id uuid, p_comment text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.recommendations%rowtype;
begin
  v := public.recommendation_for_update(p_id);
  if not public.is_technical_responsible(v.office_id) then
    raise exception 'Somente o responsável técnico devolve' using errcode = '42501';
  end if;
  if v.status not in ('em_revisao', 'aprovada') then
    raise exception 'Recomendação não está em revisão nem aprovada' using errcode = 'P0001';
  end if;
  if p_comment is null or length(trim(p_comment)) < 5 then
    raise exception 'Comentário obrigatório (mín. 5 caracteres) ao devolver' using errcode = 'P0001';
  end if;
  update public.recommendations set status = 'rascunho', approved_by = null, approved_at = null where id = p_id;
  insert into public.recommendation_events (office_id, recommendation_id, event, actor, comment)
  values (v.office_id, p_id, 'returned', auth.uid(), trim(p_comment));
end;
$$;

create or replace function public.request_report(p_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.recommendations%rowtype;
begin
  v := public.recommendation_for_update(p_id);
  if v.status <> 'aprovada' then
    raise exception 'Somente recomendação aprovada pode ser emitida' using errcode = 'P0001';
  end if;
  -- chave nova a cada pedido: reemissão após devolução/reaprovação ou falha do job anterior
  perform public.enqueue_job(v.office_id, 'emit_report', jsonb_build_object('recommendation_id', p_id),
    'report:' || p_id || ':' || txid_current());
  insert into public.recommendation_events (office_id, recommendation_id, event, actor)
  values (v.office_id, p_id, 'emission_requested', auth.uid());
end;
$$;

revoke all on function public.is_technical_responsible(uuid) from public, anon;
revoke all on function public.decision_threshold(uuid) from public, anon;
revoke all on function public.set_technical_responsible(uuid, uuid, boolean, text, text) from public, anon;
revoke all on function public.set_decision_threshold(uuid, numeric) from public, anon;
revoke all on function public.request_projection(uuid) from public, anon;
revoke all on function public.recommendation_for_update(uuid) from public, anon, authenticated;
revoke all on function public.submit_recommendation(uuid) from public, anon;
revoke all on function public.approve_recommendation(uuid) from public, anon;
revoke all on function public.return_recommendation(uuid, text) from public, anon;
revoke all on function public.request_report(uuid) from public, anon;
grant execute on function public.is_technical_responsible(uuid) to authenticated, service_role;
grant execute on function public.decision_threshold(uuid) to authenticated, service_role;
grant execute on function public.set_technical_responsible(uuid, uuid, boolean, text, text) to authenticated;
grant execute on function public.set_decision_threshold(uuid, numeric) to authenticated;
grant execute on function public.request_projection(uuid) to authenticated;
grant execute on function public.submit_recommendation(uuid) to authenticated;
grant execute on function public.approve_recommendation(uuid) to authenticated;
grant execute on function public.return_recommendation(uuid, text) to authenticated;
grant execute on function public.request_report(uuid) to authenticated;

-- ---------------------------------------------------------------- Storage: usuários não gravam relatórios emitidos
drop policy if exists documents_insert on storage.objects;
create policy documents_insert on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'documents'
    and public.is_member(public.storage_path_office(name))
    and name not like '%/exports/%'
    and name not like '%/simulations/%'
    and name not like '%/reports/%'
  );
