-- Ciclo 4 — Reforma Tributária 2027: Livro de Apuração do ICMS (documento opcional), conciliação R7, alvo de
-- mapeamento de compras, quarta alternativa (Simples híbrido), projeção por exercício e premissas de 2027 que só
-- bloqueiam o próprio exercício.

-- ---------------------------------------------------------------- Livro de Apuração do ICMS
alter table public.source_files drop constraint source_files_doc_type_check;
alter table public.source_files add constraint source_files_doc_type_check check (doc_type in (
  'PGDAS_D', 'FOLHA_ALTERDATA', 'DRE_ALTERDATA', 'BALANCETE_ALTERDATA', 'LIVRO_ICMS_ALTERDATA'
));

-- ---------------------------------------------------------------- R7: compras (livro) × conta de compras (balancete)
alter table public.reconciliations drop constraint reconciliations_rule_check;
alter table public.reconciliations add constraint reconciliations_rule_check
  check (rule in ('R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7'));

alter table public.account_mappings drop constraint account_mappings_target_check;
alter table public.account_mappings add constraint account_mappings_target_check check (target in (
  'vendas', 'simples_despesa', 'simples_a_recolher', 'inss_a_pagar', 'fgts_a_pagar', 'salarios_a_pagar',
  'compras_mercadorias'
));

-- padrão do escritório (plano Alterdata): compras de mercadorias = conta reduzida 13101
insert into public.account_mappings (office_id, target, doc_type, account_code)
select o.id, 'compras_mercadorias', 'BALANCETE_ALTERDATA', '13101'
  from public.offices o
 where not exists (select 1 from public.account_mappings m
                    where m.office_id = o.id and m.company_id is null and m.target = 'compras_mercadorias'
                      and m.doc_type = 'BALANCETE_ALTERDATA');

-- ---------------------------------------------------------------- quarta alternativa: Simples híbrido
alter table public.simulation_lines drop constraint simulation_lines_regime_check;
alter table public.simulation_lines add constraint simulation_lines_regime_check
  check (regime in ('SIMPLES', 'PRESUMIDO', 'REAL', 'SIMPLES_HIBRIDO'));
alter table public.projection_lines drop constraint projection_lines_regime_check;
alter table public.projection_lines add constraint projection_lines_regime_check
  check (regime in ('SIMPLES', 'PRESUMIDO', 'REAL', 'SIMPLES_HIBRIDO'));

-- ---------------------------------------------------------------- premissas de 2027 não bloqueiam 2026
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

-- ---------------------------------------------------------------- projeção por exercício
drop function if exists public.request_projection(uuid);

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

revoke all on function public.request_projection(uuid, integer) from public, anon;
grant execute on function public.request_projection(uuid, integer) to authenticated;

-- ---------------------------------------------------------------- reset de recomendações por exercício
-- Premissa do grupo reforma_2027 só afeta projeções de 2027 em diante: não devolve a rascunho a recomendação de 2026.
-- As demais premissas continuam devolvendo todas (2027 deriva da projeção de 2026).
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
  v_min_year integer;
begin
  if tg_op = 'DELETE' then
    if old.status <> 'confirmed' then
      return old;
    end if;
    v_case := old.case_id;
    v_label := old.key || ' ' || old.scope || ' (removida)';
    v_min_year := case when old.grp = 'reforma_2027' then 2027 else 0 end;
  elsif (new.status = 'confirmed' and (new.value is distinct from old.value or old.status <> 'confirmed'))
        or (new.status = 'pending' and old.status = 'confirmed') then
    v_case := new.case_id;
    v_label := new.key || ' ' || new.scope;
    v_min_year := case when new.grp = 'reforma_2027' then 2027 else 0 end;
  else
    return new;
  end if;
  for r in
    update public.recommendations rec set status = 'rascunho', approved_by = null, approved_at = null
      from public.projections p
     where rec.case_id = v_case and rec.status in ('em_revisao', 'aprovada')
       and p.id = rec.projection_id and p.year >= v_min_year
    returning rec.id, rec.office_id
  loop
    insert into public.recommendation_events (office_id, recommendation_id, event, actor, comment)
    values (r.office_id, r.id, 'reset_by_assumption', auth.uid(), v_label);
  end loop;
  return coalesce(new, old);
end;
$$;
