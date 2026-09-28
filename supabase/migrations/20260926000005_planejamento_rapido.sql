-- Ciclo 5 — Planejamento Rápido: dossiê de 2027 a partir da Declaração de Faturamento, folha e DRE (PDF ou
-- digitados), com CNAE consultado pela automação n8n (job lookup_company) ou digitado.

-- ---------------------------------------------------------------- tipo do dossiê
alter table public.tax_cases add column kind text not null default 'completo'
  check (kind in ('completo', 'rapido'));

-- ---------------------------------------------------------------- Declaração de Faturamento
alter table public.source_files drop constraint source_files_doc_type_check;
alter table public.source_files add constraint source_files_doc_type_check check (doc_type in (
  'PGDAS_D', 'FOLHA_ALTERDATA', 'DRE_ALTERDATA', 'BALANCETE_ALTERDATA', 'LIVRO_ICMS_ALTERDATA',
  'DECLARACAO_FATURAMENTO'
));

-- ---------------------------------------------------------------- CNAE da empresa (sem dados de sócios)
alter table public.companies
  add column cnae_principal text check (cnae_principal ~ '^[0-9]{7}$'),
  add column cnae_descricao text,
  add column cnaes_secundarios jsonb not null default '[]'::jsonb,
  add column cnae_origem text check (cnae_origem in ('receita', 'manual')),
  add column cnae_atualizado_em timestamptz,
  add column cnae_consulta_status text check (cnae_consulta_status in ('pendente', 'ok', 'falhou')),
  add column cnae_consulta_erro text;

alter table public.jobs drop constraint jobs_kind_check;
alter table public.jobs add constraint jobs_kind_check check (kind in (
  'extract', 'reconcile', 'export_xlsx', 'suggest_assumptions', 'calculate', 'export_simulation',
  'project', 'emit_report', 'lookup_company'
));

create or replace function public.request_company_lookup(p_company_id uuid)
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
  -- uma consulta por vez: cada chamada consome a cota da automação (BrasilAPI)
  if exists (select 1 from public.jobs where kind = 'lookup_company' and status in ('queued', 'running')
               and payload ->> 'company_id' = p_company_id::text) then
    raise exception 'Consulta do CNAE já em andamento — aguarde' using errcode = 'P0001';
  end if;
  update public.companies set cnae_consulta_status = 'pendente', cnae_consulta_erro = null where id = p_company_id;
  perform public.enqueue_job(v.office_id, 'lookup_company', jsonb_build_object('company_id', p_company_id),
    'lookup:' || p_company_id || ':' || txid_current());
  perform public.write_audit(v.office_id, 'company.lookup_requested', 'companies', p_company_id, null, null);
end;
$$;

create or replace function public.set_company_cnae(p_company_id uuid, p_cnae text, p_descricao text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.companies%rowtype;
  v_cnae text := regexp_replace(coalesce(p_cnae, ''), '[^0-9]', '', 'g');
begin
  select * into v from public.companies where id = p_company_id;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Empresa não encontrada' using errcode = 'P0002';
  end if;
  if v_cnae !~ '^[0-9]{7}$' then
    raise exception 'CNAE deve ter 7 dígitos (ex.: 4744-0/01)' using errcode = 'P0001';
  end if;
  update public.companies
     set cnae_principal = v_cnae, cnae_descricao = nullif(trim(coalesce(p_descricao, '')), ''),
         cnae_origem = 'manual', cnae_atualizado_em = now(), cnae_consulta_status = 'ok', cnae_consulta_erro = null
   where id = p_company_id;
  perform public.write_audit(v.office_id, 'company.cnae_set', 'companies', p_company_id,
    jsonb_build_object('cnae', v.cnae_principal), jsonb_build_object('cnae', v_cnae, 'origem', 'manual'));
end;
$$;

revoke all on function public.request_company_lookup(uuid) from public, anon;
grant execute on function public.request_company_lookup(uuid) to authenticated;
revoke all on function public.set_company_cnae(uuid, text, text) from public, anon;
grant execute on function public.set_company_cnae(uuid, text, text) to authenticated;

-- ---------------------------------------------------------------- valores digitados (sem PDF)
create table public.manual_values (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  doc_type text not null check (doc_type in ('FATURAMENTO', 'FOLHA', 'DRE')),
  competence date not null check (extract(day from competence) = 1),
  field_key text not null check (field_key in (
    'faturamento.mes', 'folha.salarios', 'folha.pro_labore', 'folha.autonomos',
    'dre.receita_bruta', 'dre.outras_receitas', 'dre.resultado'
  )),
  value numeric(15, 2) not null,
  entered_by uuid not null default auth.uid() references auth.users (id),
  entered_at timestamptz not null default now(),
  unique (case_id, doc_type, competence, field_key),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade
);

create trigger manual_values_immutable
  before insert or update or delete on public.manual_values
  for each row execute function public.tg_block_if_homologated();

alter table public.manual_values enable row level security;
revoke all on table public.manual_values from anon, authenticated;
grant select on table public.manual_values to authenticated;
create policy manual_values_select on public.manual_values
  for select to authenticated using (public.is_member(office_id));

create or replace function public.enter_manual_values(p_case_id uuid, p_doc_type text, p_competence date,
                                                      p_values jsonb)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
  v_comp date := date_trunc('month', p_competence)::date;
  v_keys text[] := case p_doc_type
    when 'FATURAMENTO' then array['faturamento.mes']
    when 'FOLHA' then array['folha.salarios', 'folha.pro_labore', 'folha.autonomos']
    when 'DRE' then array['dre.receita_bruta', 'dre.outras_receitas', 'dre.resultado'] end;
  v_pdf text := case p_doc_type
    when 'FATURAMENTO' then 'DECLARACAO_FATURAMENTO' when 'FOLHA' then 'FOLHA_ALTERDATA' when 'DRE' then 'DRE_ALTERDATA' end;
  k text;
  v_num numeric;
begin
  select * into v from public.tax_cases where id = p_case_id;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Dossiê não encontrado' using errcode = 'P0002';
  end if;
  if v.kind <> 'rapido' then
    raise exception 'Digitação de valores só no planejamento rápido' using errcode = 'P0001';
  end if;
  if v_keys is null then
    raise exception 'Documento inválido: %', p_doc_type using errcode = 'P0001';
  end if;
  if v_comp < date_trunc('month', v.period_start) or v_comp > v.period_end then
    raise exception 'Competência fora do período do dossiê' using errcode = 'P0001';
  end if;
  -- mês/documento com PDF extraído só muda por ajuste justificado (a declaração cobre os 12 meses)
  if exists (select 1 from public.extracted_values e
              where e.case_id = p_case_id and e.doc_type = v_pdf and e.competence = v_comp) then
    raise exception 'Mês com PDF extraído: altere o valor por ajuste justificado' using errcode = 'P0001';
  end if;
  if p_values is null or jsonb_typeof(p_values) <> 'object'
     or exists (select 1 from jsonb_object_keys(p_values) x where x <> all (v_keys)) then
    raise exception 'Campos válidos para %: %', p_doc_type, array_to_string(v_keys, ', ') using errcode = 'P0001';
  end if;
  foreach k in array v_keys loop
    if not (p_values ? k) then
      continue;
    end if;
    begin
      v_num := (p_values ->> k)::numeric;
    exception when others then
      raise exception 'Valor inválido em %', k using errcode = 'P0001';
    end;
    if v_num is null or (v_num < 0 and k <> 'dre.resultado') then
      raise exception 'Valor inválido em % (não pode ser negativo)', k using errcode = 'P0001';
    end if;
    insert into public.manual_values (office_id, case_id, doc_type, competence, field_key, value)
    values (v.office_id, p_case_id, p_doc_type, v_comp, k, round(v_num, 2))
    on conflict (case_id, doc_type, competence, field_key)
    do update set value = excluded.value, entered_by = auth.uid(), entered_at = now();
  end loop;
  perform public.write_audit(v.office_id, 'manual_values.entered', 'tax_cases', p_case_id, null,
    jsonb_build_object('doc_type', p_doc_type, 'competence', v_comp, 'values', p_values));
end;
$$;

create or replace function public.clear_manual_values(p_case_id uuid, p_doc_type text, p_competence date)
returns void
language plpgsql
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
  delete from public.manual_values
   where case_id = p_case_id and doc_type = p_doc_type and competence = date_trunc('month', p_competence)::date;
  perform public.write_audit(v.office_id, 'manual_values.cleared', 'tax_cases', p_case_id, null,
    jsonb_build_object('doc_type', p_doc_type, 'competence', p_competence));
end;
$$;

revoke all on function public.enter_manual_values(uuid, text, date, jsonb) from public, anon;
grant execute on function public.enter_manual_values(uuid, text, date, jsonb) to authenticated;
revoke all on function public.clear_manual_values(uuid, text, date) from public, anon;
grant execute on function public.clear_manual_values(uuid, text, date) to authenticated;

-- ---------------------------------------------------------------- homologação por tipo de dossiê
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

revoke all on function public.rapido_blockers(uuid) from public, anon;
grant execute on function public.rapido_blockers(uuid) to authenticated;

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

  if not exists (select 1 from public.source_files where case_id = p_case_id)
     and not (v_case.kind = 'rapido' and exists (select 1 from public.manual_values where case_id = p_case_id)) then
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
  if v_case.kind = 'rapido' then
    v_blockers := v_blockers || public.rapido_blockers(p_case_id);
  end if;

  if array_length(v_blockers, 1) > 0 then
    raise exception 'Homologação bloqueada: %', array_to_string(v_blockers, '; ')
      using errcode = 'P0001';
  end if;

  select jsonb_build_object(
    'schema_version', 1,
    'case', jsonb_build_object(
      'id', v_case.id, 'office_id', v_case.office_id,
      'period_start', v_case.period_start, 'period_end', v_case.period_end)
      || case when v_case.kind = 'rapido' then jsonb_build_object('kind', 'rapido') else '{}'::jsonb end,
    'company', (select jsonb_build_object('id', co.id, 'cnpj', co.cnpj, 'legal_name', co.legal_name)
                       || case when v_case.kind = 'rapido' then jsonb_build_object(
                            'cnae_principal', co.cnae_principal, 'cnae_descricao', co.cnae_descricao,
                            'cnaes_secundarios', co.cnaes_secundarios, 'cnae_origem', co.cnae_origem)
                          else '{}'::jsonb end
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
  ) || case when v_case.kind = 'rapido' then jsonb_build_object(
         'manual_values', coalesce((select jsonb_agg(jsonb_build_object(
            'id', m.id, 'doc_type', m.doc_type, 'competence', m.competence, 'field_key', m.field_key,
            'value', m.value, 'entered_by', m.entered_by, 'entered_at', m.entered_at)
            order by m.doc_type, m.competence, m.field_key)
          from public.manual_values m where m.case_id = p_case_id), '[]'::jsonb))
       else '{}'::jsonb end
  into v_content;

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

-- ---------------------------------------------------------------- cálculo e projeção por tipo de dossiê
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
  if v.kind = 'rapido' then
    raise exception 'O planejamento rápido compara só 2027: use Projetar 2027' using errcode = 'P0001';
  end if;
  -- o grupo reforma_2027 (alíquotas de CBS/IBS, crescimento, base de créditos) só bloqueia a projeção de 2027
  select count(*), array_agg(label order by grp, key, scope) filter (where status = 'pending' and grp <> 'reforma_2027')
    into v_total, v_pending
    from public.assumptions where case_id = p_case_id;
  if v_total = 0 then
    raise exception 'Gere as premissas do planejamento antes de calcular' using errcode = 'P0001';
  end if;
  if array_length(v_pending, 1) > 0 then
    raise exception 'Premissas pendentes de confirmação: %', array_to_string(v_pending, '; ') using errcode = 'P0001';
  end if;
  perform public.enqueue_job(v.office_id, 'calculate',
    jsonb_build_object('case_id', p_case_id, 'requested_by', auth.uid()),
    'calculate:' || p_case_id || ':' || txid_current());
  perform public.write_audit(v.office_id, 'calculation.requested', 'tax_cases', p_case_id, null, null);
end;
$$;

create or replace function public.request_projection(p_case_id uuid, p_year integer default 2026)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
begin
  v := public.planning_case(p_case_id);
  if p_year not in (2026, 2027) then
    raise exception 'Exercício % sem regras parametrizadas', p_year using errcode = 'P0001';
  end if;
  if v.kind = 'rapido' and p_year <> 2027 then
    raise exception 'O planejamento rápido projeta só 2027' using errcode = 'P0001';
  end if;
  if not exists (select 1 from public.assumptions where case_id = p_case_id) then
    raise exception 'Gere as premissas do planejamento antes de projetar' using errcode = 'P0001';
  end if;
  perform public.enqueue_job(v.office_id, 'project',
    jsonb_build_object('case_id', p_case_id, 'year', p_year, 'requested_by', auth.uid()),
    'project:' || p_case_id || ':' || p_year || ':' || txid_current());
  perform public.write_audit(v.office_id, 'projection.requested', 'tax_cases', p_case_id, null,
    jsonb_build_object('year', p_year));
end;
$$;
