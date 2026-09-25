-- Auditoria append-only, snapshots imutáveis, bloqueio de escrita em dossiês homologados
-- e a função de homologação.

create table public.audit_events (
  id bigint generated always as identity primary key,
  office_id uuid not null references public.offices (id) on delete cascade,
  actor uuid,
  event text not null,
  entity text not null,
  entity_id uuid,
  before jsonb,
  after jsonb,
  created_at timestamptz not null default now()
);

create index audit_events_office_idx on public.audit_events (office_id, created_at desc);

create table public.snapshots (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null unique,
  content jsonb not null,
  sha256 char(64) not null,
  created_by uuid references auth.users (id),
  created_at timestamptz not null default now(),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade
);

-- ---------------------------------------------------------------- append-only
create or replace function public.tg_append_only()
returns trigger
language plpgsql
as $$
begin
  raise exception '% é somente inclusão (append-only)', tg_table_name using errcode = 'P0001';
end;
$$;

create trigger audit_events_append_only
  before update or delete on public.audit_events
  for each row execute function public.tg_append_only();
create trigger snapshots_append_only
  before update or delete on public.snapshots
  for each row execute function public.tg_append_only();

-- ---------------------------------------------------------------- imutabilidade do dossiê homologado
create or replace function public.tg_block_if_homologated()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_case uuid;
begin
  v_case := case when tg_op = 'DELETE' then old.case_id else new.case_id end;
  if exists (select 1 from public.tax_cases where id = v_case and status = 'homologated') then
    raise exception 'Dossiê homologado: alteração não permitida' using errcode = 'P0001';
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end;
$$;

create trigger source_files_immutable
  before insert or update or delete on public.source_files
  for each row execute function public.tg_block_if_homologated();
create trigger extracted_values_immutable
  before insert or update or delete on public.extracted_values
  for each row execute function public.tg_block_if_homologated();
create trigger value_adjustments_immutable
  before insert or update or delete on public.value_adjustments
  for each row execute function public.tg_block_if_homologated();
create trigger validations_immutable
  before insert or update or delete on public.validations
  for each row execute function public.tg_block_if_homologated();
create trigger reconciliations_immutable
  before insert or update or delete on public.reconciliations
  for each row execute function public.tg_block_if_homologated();

create or replace function public.tg_tax_cases_immutable()
returns trigger
language plpgsql
as $$
begin
  if old.status = 'homologated' then
    raise exception 'Dossiê homologado: alteração não permitida' using errcode = 'P0001';
  end if;
  return new;
end;
$$;

create trigger tax_cases_immutable
  before update on public.tax_cases
  for each row execute function public.tg_tax_cases_immutable();

-- ---------------------------------------------------------------- trilha de auditoria
create or replace function public.write_audit(
  p_office uuid, p_event text, p_entity text, p_entity_id uuid, p_before jsonb, p_after jsonb
) returns void
language sql
security definer
set search_path = public
as $$
  insert into public.audit_events (office_id, actor, event, entity, entity_id, before, after)
  values (p_office, auth.uid(), p_event, p_entity, p_entity_id, p_before, p_after);
$$;

revoke all on function public.write_audit(uuid, text, text, uuid, jsonb, jsonb) from public, anon, authenticated;

create or replace function public.tg_audit_source_files()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.write_audit(new.office_id, 'file.uploaded', 'source_files', new.id, null,
    jsonb_build_object('case_id', new.case_id, 'sha256', new.sha256, 'original_name', new.original_name));
  return new;
end;
$$;

create trigger source_files_audit
  after insert on public.source_files
  for each row execute function public.tg_audit_source_files();

create or replace function public.tg_audit_reclassify()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.doc_type is distinct from old.doc_type and auth.uid() is not null then
    perform public.write_audit(new.office_id, 'file.reclassified', 'source_files', new.id,
      jsonb_build_object('doc_type', old.doc_type), jsonb_build_object('doc_type', new.doc_type));
  end if;
  return new;
end;
$$;

create trigger source_files_audit_reclassify
  after update of doc_type on public.source_files
  for each row execute function public.tg_audit_reclassify();

create or replace function public.tg_audit_value_adjustments()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.write_audit(new.office_id, 'value.adjusted', 'extracted_values', new.value_id,
    jsonb_build_object('value', new.old_value),
    jsonb_build_object('value', new.new_value, 'reason', new.reason, 'adjustment_id', new.id));
  return new;
end;
$$;

create trigger value_adjustments_audit
  after insert on public.value_adjustments
  for each row execute function public.tg_audit_value_adjustments();

create or replace function public.tg_audit_justification()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.justification is distinct from old.justification and auth.uid() is not null then
    perform public.write_audit(new.office_id, 'reconciliation.justified', 'reconciliations', new.id,
      jsonb_build_object('justification', old.justification),
      jsonb_build_object('justification', new.justification, 'rule', new.rule, 'competence', new.competence));
  end if;
  return new;
end;
$$;

create trigger reconciliations_audit
  after update on public.reconciliations
  for each row execute function public.tg_audit_justification();

create or replace function public.tg_audit_export()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.kind = 'export_xlsx' then
    perform public.write_audit(new.office_id, 'export.requested', 'jobs', new.id, null, new.payload);
  end if;
  return new;
end;
$$;

create trigger jobs_audit_export
  after insert on public.jobs
  for each row execute function public.tg_audit_export();

-- ---------------------------------------------------------------- mudança de tolerância
-- Reconcilia de novo todos os dossiês abertos do escritório com a nova tolerância.
create or replace function public.tg_offices_tolerance_reconcile()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_case uuid;
begin
  if (new.settings ->> 'tolerance_brl') is distinct from (old.settings ->> 'tolerance_brl') then
    for v_case in
      select id from public.tax_cases where office_id = new.id and status <> 'homologated'
    loop
      perform public.enqueue_job(new.id, 'reconcile', jsonb_build_object('case_id', v_case),
        'reconcile:' || v_case || ':tolerance:' || (new.settings ->> 'tolerance_brl') || ':' || txid_current());
    end loop;
    perform public.write_audit(new.id, 'office.tolerance_changed', 'offices', new.id,
      jsonb_build_object('tolerance_brl', old.settings -> 'tolerance_brl'),
      jsonb_build_object('tolerance_brl', new.settings -> 'tolerance_brl'));
  end if;
  return new;
end;
$$;

create trigger offices_tolerance_reconcile
  after update of settings on public.offices
  for each row execute function public.tg_offices_tolerance_reconcile();

-- ---------------------------------------------------------------- homologação
create or replace function public.homologate_case(p_case_id uuid)
returns table (snapshot_id uuid, sha256 text)
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_case public.tax_cases%rowtype;
  v_blockers text[] := '{}';
  v_content jsonb;
  v_hash text;
  v_id uuid;
begin
  select * into v_case from public.tax_cases where id = p_case_id for update;
  if not found or not public.is_member(v_case.office_id) then
    raise exception 'Dossiê não encontrado' using errcode = 'P0002';
  end if;
  if v_case.status = 'homologated' then
    raise exception 'Dossiê já homologado' using errcode = 'P0001';
  end if;

  if not exists (select 1 from public.source_files where case_id = p_case_id) then
    v_blockers := v_blockers || 'Nenhum arquivo enviado'::text;
  end if;
  -- Conciliação precisa estar atualizada (ajuste ou mudança de tolerância ainda na fila).
  if exists (select 1 from public.jobs
              where office_id = v_case.office_id and kind in ('extract', 'reconcile')
                and status in ('queued', 'running') and payload ->> 'case_id' = p_case_id::text) then
    v_blockers := v_blockers || 'Processamento/conciliação em andamento — aguarde e tente novamente'::text;
  end if;
  select v_blockers || coalesce(array_agg(
           coalesce(original_name, id::text) || ': ' ||
           case status
             when 'uploaded' then 'aguardando processamento'
             when 'processing' then 'em processamento'
             when 'failed' then 'falha na extração'
             when 'rejected' then 'rejeitado'
             when 'unclassified' then 'não classificado'
             when 'cnpj_mismatch' then 'CNPJ divergente'
           end order by original_name), '{}')
    into v_blockers
    from public.source_files
   where case_id = p_case_id and status <> 'extracted';
  select v_blockers || coalesce(array_agg(
           rule || ' ' || to_char(competence, 'MM/YYYY') || ': divergência sem justificativa'
           order by competence, rule), '{}')
    into v_blockers
    from public.reconciliations
   where case_id = p_case_id and status = 'divergent'
     and (justification is null or length(trim(justification)) < 5);

  if array_length(v_blockers, 1) > 0 then
    raise exception 'Homologação bloqueada: %', array_to_string(v_blockers, '; ')
      using errcode = 'P0001';
  end if;

  select jsonb_build_object(
    'schema_version', 1,
    'case', jsonb_build_object(
      'id', v_case.id, 'office_id', v_case.office_id,
      'period_start', v_case.period_start, 'period_end', v_case.period_end),
    'company', (select jsonb_build_object('id', co.id, 'cnpj', co.cnpj, 'legal_name', co.legal_name)
                  from public.companies co where co.id = v_case.company_id),
    'tolerance_brl', (select (o.settings ->> 'tolerance_brl')::numeric
                        from public.offices o where o.id = v_case.office_id),
    'files', coalesce((select jsonb_agg(jsonb_build_object(
        'id', f.id, 'original_name', f.original_name, 'sha256', f.sha256, 'doc_type', f.doc_type,
        'competence', f.competence, 'parser_version', f.parser_version,
        'result_hash', f.result_hash, 'pages', f.pages) order by f.doc_type, f.competence, f.id)
      from public.source_files f where f.case_id = p_case_id), '[]'::jsonb),
    'values', coalesce((select jsonb_agg(jsonb_build_object(
        'id', e.id, 'file_id', e.file_id, 'ordinal', e.ordinal, 'doc_type', e.doc_type,
        'competence', e.competence, 'section', e.section, 'field_key', e.field_key,
        'label', e.label, 'account_code', e.account_code, 'column', e.column_name,
        'value', e.effective_value, 'original_value', e.value, 'adjusted', e.adjusted,
        'nature', e.nature, 'page', e.page, 'bbox', e.bbox) order by e.file_id, e.ordinal)
      from public.effective_values e where e.case_id = p_case_id), '[]'::jsonb),
    'adjustments', coalesce((select jsonb_agg(jsonb_build_object(
        'id', a.id, 'value_id', a.value_id, 'old_value', a.old_value, 'new_value', a.new_value,
        'reason', a.reason, 'author', a.author, 'created_at', a.created_at) order by a.created_at, a.id)
      from public.value_adjustments a where a.case_id = p_case_id), '[]'::jsonb),
    'validations', coalesce((select jsonb_agg(jsonb_build_object(
        'file_id', v.file_id, 'rule', v.rule, 'status', v.status, 'expected', v.expected,
        'actual', v.actual, 'diff', v.diff, 'detail', v.detail) order by v.file_id, v.rule)
      from public.validations v where v.case_id = p_case_id), '[]'::jsonb),
    'reconciliations', coalesce((select jsonb_agg(jsonb_build_object(
        'competence', r.competence, 'rule', r.rule, 'description', r.description,
        'left_label', r.left_label, 'left_value', r.left_value,
        'right_label', r.right_label, 'right_value', r.right_value,
        'diff', r.diff, 'tolerance', r.tolerance, 'status', r.status,
        'justification', r.justification, 'justified_by', r.justified_by,
        'justified_at', r.justified_at) order by r.competence, r.rule)
      from public.reconciliations r where r.case_id = p_case_id), '[]'::jsonb),
    'homologated_by', auth.uid(),
    'homologated_at', now()
  ) into v_content;

  v_hash := encode(extensions.digest(v_content::text, 'sha256'), 'hex');

  insert into public.snapshots (office_id, case_id, content, sha256, created_by)
  values (v_case.office_id, p_case_id, v_content, v_hash, auth.uid())
  returning id into v_id;

  update public.tax_cases set status = 'homologated' where id = p_case_id;

  perform public.write_audit(v_case.office_id, 'case.homologated', 'tax_cases', p_case_id,
    jsonb_build_object('status', v_case.status),
    jsonb_build_object('status', 'homologated', 'snapshot_id', v_id, 'sha256', v_hash));

  return query select v_id, v_hash;
end;
$$;

alter table public.audit_events enable row level security;
alter table public.snapshots enable row level security;

revoke all on table public.audit_events from anon, authenticated;
revoke all on table public.snapshots from anon, authenticated;
grant select on table public.audit_events to authenticated;
grant select on table public.snapshots to authenticated;

create policy audit_events_select on public.audit_events
  for select to authenticated using (public.is_member(office_id));
create policy snapshots_select on public.snapshots
  for select to authenticated using (public.is_member(office_id));

revoke all on function public.homologate_case(uuid) from public, anon;
grant execute on function public.homologate_case(uuid) to authenticated;
revoke all on function public.request_xlsx_export(uuid) from public, anon;
grant execute on function public.request_xlsx_export(uuid) to authenticated;
