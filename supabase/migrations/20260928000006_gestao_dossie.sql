-- Gestão do dossiê (pós-ciclo 5): razão social pela consulta do CNPJ; excluir dossiê, arquivo e empresa; editar
-- período/tipo do dossiê e dados da empresa; reabrir dossiê homologado. Decisão do usuário (2026-09-28): qualquer
-- membro do escritório pode reabrir ou excluir, sem restrição — inclusive snapshot, recomendações e PDFs emitidos.
-- A trilha de auditoria continua somente inclusão (registra quem, quando e o motivo).

-- ---------------------------------------------------------------- liberação controlada das proteções
-- As funções abaixo (security definer) marcam a transação com app.purge_case = <id do dossiê>. Os gatilhos de
-- imutabilidade só deixam passar exclusões desse dossiê; authenticated não tem permissão de DELETE direto nessas tabelas.
create or replace function public.purging_case(p_case uuid)
returns boolean
language sql
stable
as $$
  select p_case is not null and coalesce(current_setting('app.purge_case', true), '') = p_case::text;
$$;

create or replace function public.tg_append_only()
returns trigger
language plpgsql
as $$
begin
  -- exclusão pelo purge_case/reopen_case (auditoria nunca é liberada)
  if tg_op = 'DELETE' and tg_table_name <> 'audit_events' and coalesce(current_setting('app.purge_case', true), '') <> '' then
    return old;
  end if;
  raise exception '% é somente inclusão (append-only)', tg_table_name using errcode = 'P0001';
end;
$$;

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
  if tg_op = 'DELETE' and public.purging_case(v_case) then
    return old;
  end if;
  if exists (select 1 from public.tax_cases where id = v_case and status = 'homologated') then
    raise exception 'Dossiê homologado: alteração não permitida' using errcode = 'P0001';
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end;
$$;

create or replace function public.tg_recommendation_emitted_immutable()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'DELETE' then
    if old.status = 'emitida' and not public.purging_case(old.case_id) then
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

create or replace function public.tg_tax_cases_immutable()
returns trigger
language plpgsql
as $$
begin
  if old.status = 'homologated' and not public.purging_case(old.id) then
    raise exception 'Dossiê homologado: alteração não permitida' using errcode = 'P0001';
  end if;
  return new;
end;
$$;

-- ---------------------------------------------------------------- limpeza de arquivos no Storage (worker)
alter table public.jobs drop constraint jobs_kind_check;
alter table public.jobs add constraint jobs_kind_check check (kind in (
  'extract', 'reconcile', 'export_xlsx', 'suggest_assumptions', 'calculate', 'export_simulation',
  'project', 'emit_report', 'lookup_company', 'purge_storage'
));

-- ---------------------------------------------------------------- razão social pela consulta do CNPJ
alter table public.companies add column razao_social_pendente boolean not null default false;

create or replace function public.update_company(p_company_id uuid, p_legal_name text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.companies%rowtype;
  v_name text := trim(coalesce(p_legal_name, ''));
begin
  select * into v from public.companies where id = p_company_id;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Empresa não encontrada' using errcode = 'P0002';
  end if;
  if length(v_name) < 2 then
    raise exception 'Informe a razão social' using errcode = 'P0001';
  end if;
  update public.companies set legal_name = v_name, razao_social_pendente = false where id = p_company_id;
  perform public.write_audit(v.office_id, 'company.updated', 'companies', p_company_id,
    jsonb_build_object('legal_name', v.legal_name), jsonb_build_object('legal_name', v_name));
end;
$$;

create or replace function public.delete_company(p_company_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.companies%rowtype;
begin
  select * into v from public.companies where id = p_company_id;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Empresa não encontrada' using errcode = 'P0002';
  end if;
  if exists (select 1 from public.tax_cases where company_id = p_company_id) then
    raise exception 'A empresa tem dossiês: exclua os dossiês antes' using errcode = 'P0001';
  end if;
  delete from public.jobs where kind = 'lookup_company' and status in ('queued', 'running')
     and payload ->> 'company_id' = p_company_id::text;
  delete from public.companies where id = p_company_id;
  perform public.write_audit(v.office_id, 'company.deleted', 'companies', p_company_id,
    jsonb_build_object('cnpj', v.cnpj, 'legal_name', v.legal_name), null);
end;
$$;

-- ---------------------------------------------------------------- editar dossiê (antes da homologação)
create or replace function public.update_case(p_case_id uuid, p_period_start date, p_period_end date, p_kind text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
  v_start date := date_trunc('month', p_period_start)::date;
  v_end date := (date_trunc('month', p_period_end) + interval '1 month - 1 day')::date;
begin
  select * into v from public.tax_cases where id = p_case_id for update;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Dossiê não encontrado' using errcode = 'P0002';
  end if;
  if v.status = 'homologated' then
    raise exception 'Dossiê homologado: reabra o dossiê para editar' using errcode = 'P0001';
  end if;
  if p_kind not in ('completo', 'rapido') then
    raise exception 'Tipo de dossiê inválido' using errcode = 'P0001';
  end if;
  if v_end < v_start then
    raise exception 'O fim do período deve ser após o início' using errcode = 'P0001';
  end if;
  if p_kind = 'rapido' and (v_end - v_start) not between 360 and 366 then
    raise exception 'O planejamento rápido usa os últimos 12 meses' using errcode = 'P0001';
  end if;
  -- valores digitados só existem no rápido e dentro do período
  delete from public.manual_values
   where case_id = p_case_id and (p_kind <> 'rapido' or competence < v_start or competence > v_end);
  update public.tax_cases set period_start = v_start, period_end = v_end, kind = p_kind where id = p_case_id;
  if p_kind = 'rapido' then
    delete from public.reconciliations where case_id = p_case_id;     -- sem R1–R7 no rápido
  else
    perform public.enqueue_job(v.office_id, 'reconcile', jsonb_build_object('case_id', p_case_id),
      'reconcile:' || p_case_id || ':edit:' || txid_current());
  end if;
  perform public.write_audit(v.office_id, 'case.updated', 'tax_cases', p_case_id,
    jsonb_build_object('period_start', v.period_start, 'period_end', v.period_end, 'kind', v.kind),
    jsonb_build_object('period_start', v_start, 'period_end', v_end, 'kind', p_kind));
end;
$$;

-- ---------------------------------------------------------------- excluir arquivo (antes da homologação)
create or replace function public.delete_source_file(p_file_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  f public.source_files%rowtype;
  c public.tax_cases%rowtype;
begin
  select * into f from public.source_files where id = p_file_id;
  if not found or not public.is_member(f.office_id) then
    raise exception 'Arquivo não encontrado' using errcode = 'P0002';
  end if;
  select * into c from public.tax_cases where id = f.case_id;
  if c.status = 'homologated' then
    raise exception 'Dossiê homologado: reabra o dossiê para excluir arquivos' using errcode = 'P0001';
  end if;
  delete from public.jobs where kind = 'extract' and status in ('queued', 'running')
     and payload ->> 'file_id' = p_file_id::text;
  delete from public.value_adjustments a using public.extracted_values e
   where a.value_id = e.id and e.file_id = p_file_id;
  delete from public.source_files where id = p_file_id;             -- valores e validações em cascata
  perform public.enqueue_job(f.office_id, 'purge_storage',
    jsonb_build_object('case_id', f.case_id, 'paths', jsonb_build_array(f.storage_path)),
    'purge:file:' || p_file_id);
  if c.kind = 'completo' then
    perform public.enqueue_job(f.office_id, 'reconcile', jsonb_build_object('case_id', f.case_id),
      'reconcile:' || f.case_id || ':delete:' || p_file_id);
  end if;
  perform public.write_audit(f.office_id, 'file.deleted', 'source_files', p_file_id,
    jsonb_build_object('original_name', f.original_name, 'doc_type', f.doc_type, 'sha256', f.sha256), null);
end;
$$;

-- ---------------------------------------------------------------- reabrir dossiê homologado
create or replace function public.reopen_case(p_case_id uuid, p_reason text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
  v_sha text;
begin
  select * into v from public.tax_cases where id = p_case_id for update;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Dossiê não encontrado' using errcode = 'P0002';
  end if;
  if v.status <> 'homologated' then
    raise exception 'Dossiê não está homologado' using errcode = 'P0001';
  end if;
  if length(trim(coalesce(p_reason, ''))) < 5 then
    raise exception 'Informe o motivo (mín. 5 caracteres)' using errcode = 'P0001';
  end if;
  select sha256 into v_sha from public.snapshots where case_id = p_case_id;
  perform set_config('app.purge_case', p_case_id::text, true);
  -- resultados derivados do snapshot (inclusive recomendações e PDFs emitidos); premissas ficam para a nova sugestão
  delete from public.recommendations where case_id = p_case_id;
  delete from public.projections where case_id = p_case_id;
  delete from public.simulations where case_id = p_case_id;
  delete from public.snapshots where case_id = p_case_id;
  update public.tax_cases set status = 'review' where id = p_case_id;
  perform set_config('app.purge_case', '', true);
  perform public.enqueue_job(v.office_id, 'purge_storage',
    jsonb_build_object('case_id', p_case_id, 'prefixes', jsonb_build_array(
      v.office_id || '/' || p_case_id || '/reports/', v.office_id || '/' || p_case_id || '/exports/',
      v.office_id || '/' || p_case_id || '/simulations/')),
    'purge:reopen:' || p_case_id || ':' || txid_current());
  perform public.write_audit(v.office_id, 'case.reopened', 'tax_cases', p_case_id,
    jsonb_build_object('status', 'homologated', 'snapshot_sha256', v_sha),
    jsonb_build_object('status', 'review', 'reason', trim(p_reason)));
end;
$$;

-- ---------------------------------------------------------------- excluir dossiê (homologado ou não)
create or replace function public.delete_case(p_case_id uuid, p_reason text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
  v_sha text;
  v_files integer;
begin
  select * into v from public.tax_cases where id = p_case_id for update;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Dossiê não encontrado' using errcode = 'P0002';
  end if;
  if length(trim(coalesce(p_reason, ''))) < 5 then
    raise exception 'Informe o motivo (mín. 5 caracteres)' using errcode = 'P0001';
  end if;
  select sha256 into v_sha from public.snapshots where case_id = p_case_id;
  select count(*) into v_files from public.source_files where case_id = p_case_id;
  perform set_config('app.purge_case', p_case_id::text, true);
  delete from public.jobs where status in ('queued', 'running') and payload ->> 'case_id' = p_case_id::text;
  delete from public.recommendations where case_id = p_case_id;
  delete from public.projections where case_id = p_case_id;
  delete from public.simulations where case_id = p_case_id;
  delete from public.snapshots where case_id = p_case_id;
  delete from public.assumptions where case_id = p_case_id;
  delete from public.value_adjustments where case_id = p_case_id;
  delete from public.reconciliations where case_id = p_case_id;
  delete from public.manual_values where case_id = p_case_id;
  delete from public.source_files where case_id = p_case_id;
  delete from public.tax_cases where id = p_case_id;
  perform set_config('app.purge_case', '', true);
  perform public.enqueue_job(v.office_id, 'purge_storage',
    jsonb_build_object('case_id', p_case_id, 'prefixes', jsonb_build_array(v.office_id || '/' || p_case_id || '/')),
    'purge:case:' || p_case_id);
  perform public.write_audit(v.office_id, 'case.deleted', 'tax_cases', p_case_id,
    jsonb_build_object('status', v.status, 'kind', v.kind, 'period_start', v.period_start, 'period_end', v.period_end,
                       'company_id', v.company_id, 'snapshot_sha256', v_sha, 'files', v_files),
    jsonb_build_object('reason', trim(p_reason)));
end;
$$;

-- ---------------------------------------------------------------- homologação: razão social pendente bloqueia
create or replace function public.rapido_blockers(p_case_id uuid)
returns text[]
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
  v_out text[] := '{}';
  v_missing text[];
begin
  select * into v from public.tax_cases where id = p_case_id;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Dossiê não encontrado' using errcode = 'P0002';
  end if;
  if exists (select 1 from public.companies c where c.id = v.company_id and c.razao_social_pendente) then
    v_out := v_out || 'Razão social da empresa pendente (consulta à Receita ou digitação)'::text;
  end if;
  if v.kind <> 'rapido' then
    return v_out;
  end if;
  if (v.period_end - v.period_start) not between 360 and 366
     or date_trunc('month', v.period_start) <> v.period_start then
    v_out := v_out || 'O período do planejamento rápido deve ter 12 meses (do dia 1º ao fim do 12º mês)'::text;
  end if;
  select array_agg(to_char(m, 'MM/YYYY') order by m) into v_missing
    from generate_series(v.period_start, v.period_end, interval '1 month') m
   where not exists (select 1 from public.effective_values e
                      where e.case_id = p_case_id and e.doc_type = 'DECLARACAO_FATURAMENTO'
                        and e.field_key = 'faturamento.mes' and e.competence = m::date)
     and not exists (select 1 from public.manual_values mv
                      where mv.case_id = p_case_id and mv.doc_type = 'FATURAMENTO' and mv.competence = m::date);
  if array_length(v_missing, 1) > 0 then
    v_out := v_out || ('Faturamento ausente: ' || array_to_string(v_missing, ', '));
  end if;
  if not exists (select 1 from public.source_files f where f.case_id = p_case_id and f.status = 'extracted'
                    and f.doc_type = 'FOLHA_ALTERDATA')
     and not exists (select 1 from public.manual_values mv where mv.case_id = p_case_id and mv.doc_type = 'FOLHA') then
    v_out := v_out || 'Informe a folha de ao menos um mês (PDF ou digitação)'::text;
  end if;
  if not exists (select 1 from public.source_files f where f.case_id = p_case_id and f.status = 'extracted'
                    and f.doc_type = 'DRE_ALTERDATA')
     and not exists (select 1 from public.manual_values mv where mv.case_id = p_case_id and mv.doc_type = 'DRE') then
    v_out := v_out || 'Informe a DRE de ao menos um mês (PDF ou digitação)'::text;
  end if;
  select v_out || coalesce(array_agg(coalesce(f.original_name, f.id::text) || ': validação ' || va.rule || ' falhou'
                                     order by f.original_name, va.rule), '{}')
    into v_out
    from public.validations va join public.source_files f on f.id = va.file_id
   where va.case_id = p_case_id and va.status = 'fail';
  if not exists (select 1 from public.companies c where c.id = v.company_id and c.cnae_principal is not null) then
    v_out := v_out || 'Informe o CNAE principal da empresa (consulta à Receita ou digitação)'::text;
  end if;
  return v_out;
end;
$$;

-- homologate_case chama rapido_blockers para todos os tipos (a razão social pendente vale também no completo)
do $$
declare
  v_def text := pg_get_functiondef('public.homologate_case(uuid)'::regprocedure);
begin
  v_def := replace(v_def,
    'if v_case.kind = ''rapido'' then
    v_blockers := v_blockers || public.rapido_blockers(p_case_id);
  end if;',
    'v_blockers := v_blockers || public.rapido_blockers(p_case_id);');
  execute v_def;
end;
$$;

revoke all on function public.update_company(uuid, text) from public, anon;
grant execute on function public.update_company(uuid, text) to authenticated;
revoke all on function public.delete_company(uuid) from public, anon;
grant execute on function public.delete_company(uuid) to authenticated;
revoke all on function public.update_case(uuid, date, date, text) from public, anon;
grant execute on function public.update_case(uuid, date, date, text) to authenticated;
revoke all on function public.delete_source_file(uuid) from public, anon;
grant execute on function public.delete_source_file(uuid) to authenticated;
revoke all on function public.reopen_case(uuid, text) from public, anon;
grant execute on function public.reopen_case(uuid, text) to authenticated;
revoke all on function public.delete_case(uuid, text) from public, anon;
grant execute on function public.delete_case(uuid, text) to authenticated;
