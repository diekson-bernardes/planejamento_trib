-- Ciclo 6 — atividades mistas no planejamento rápido: CNAEs marcados (principal, secundários da Receita ou digitados)
-- com o percentual do faturamento de cada um. Editáveis só antes da homologação; a soma precisa ser exatamente 100,00%.
-- Sem linhas gravadas, o worker usa o CNAE principal com 100% (dossiês anteriores ao ciclo 6).

create table public.case_activities (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  cnae text not null check (cnae ~ '^[0-9]{7}$'),
  descricao text check (length(descricao) <= 300),
  percentual numeric(5, 2) not null check (percentual > 0 and percentual <= 100),
  origem text not null default 'manual' check (origem in ('receita', 'manual')),
  entered_by uuid not null default auth.uid() references auth.users (id),
  entered_at timestamptz not null default now(),
  unique (case_id, cnae),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade
);

create trigger case_activities_immutable
  before insert or update or delete on public.case_activities
  for each row execute function public.tg_block_if_homologated();

alter table public.case_activities enable row level security;
revoke all on table public.case_activities from anon, authenticated;
grant select on table public.case_activities to authenticated;
create policy case_activities_select on public.case_activities
  for select to authenticated using (public.is_member(office_id));

-- ---------------------------------------------------------------- gravação (substitui o conjunto inteiro)
create or replace function public.set_case_activities(p_case_id uuid, p_items jsonb)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.tax_cases%rowtype;
  v_items jsonb := coalesce(p_items, '[]'::jsonb);
  v_n integer;
  v_total numeric;
begin
  select * into v from public.tax_cases where id = p_case_id;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Dossiê não encontrado' using errcode = '42501';
  end if;
  if v.kind <> 'rapido' then
    raise exception 'Atividades só no planejamento rápido' using errcode = 'P0001';
  end if;
  if jsonb_typeof(v_items) <> 'array' or jsonb_array_length(v_items) = 0 then
    raise exception 'Marque ao menos uma atividade' using errcode = 'P0001';
  end if;
  v_n := jsonb_array_length(v_items);
  if exists (select 1 from jsonb_array_elements(v_items) i
              where coalesce(regexp_replace(i ->> 'cnae', '[^0-9]', '', 'g'), '') !~ '^[0-9]{7}$') then
    raise exception 'CNAE inválido (informe os 7 dígitos)' using errcode = 'P0001';
  end if;
  if (select count(distinct regexp_replace(i ->> 'cnae', '[^0-9]', '', 'g')) from jsonb_array_elements(v_items) i) <> v_n then
    raise exception 'CNAE repetido na lista de atividades' using errcode = 'P0001';
  end if;
  if v_n > 1 then
    if exists (select 1 from jsonb_array_elements(v_items) i
                where (i ->> 'percentual') is null or (i ->> 'percentual') !~ '^[0-9]+(\.[0-9]{1,2})?$'
                   or (i ->> 'percentual')::numeric <= 0) then
      raise exception 'Informe o percentual de cada atividade (maior que zero, até 2 casas)' using errcode = 'P0001';
    end if;
    select sum((i ->> 'percentual')::numeric) into v_total from jsonb_array_elements(v_items) i;
    if v_total <> 100 then
      raise exception 'A soma dos percentuais é %, precisa ser exatamente 100,00%%',
        replace(to_char(v_total, 'FM990.00'), '.', ',') || '%' using errcode = 'P0001';
    end if;
  end if;

  delete from public.case_activities where case_id = p_case_id;       -- o trigger recusa se homologado
  insert into public.case_activities (office_id, case_id, cnae, descricao, percentual, origem)
  select v.office_id, p_case_id, regexp_replace(i ->> 'cnae', '[^0-9]', '', 'g'),
         left(nullif(trim(coalesce(i ->> 'descricao', '')), ''), 300),
         case when v_n = 1 then 100 else (i ->> 'percentual')::numeric end,
         case when i ->> 'origem' = 'receita' then 'receita' else 'manual' end
    from jsonb_array_elements(v_items) i;
  if not found then
    raise exception 'Nenhuma atividade gravada' using errcode = 'P0001';
  end if;
  perform public.write_audit(v.office_id, 'case_activities.set', 'tax_cases', p_case_id, null,
    jsonb_build_object('cnaes', (select jsonb_agg(regexp_replace(i ->> 'cnae', '[^0-9]', '', 'g'))
                                   from jsonb_array_elements(v_items) i)));
end;
$$;

revoke all on function public.set_case_activities(uuid, jsonb) from public, anon;
grant execute on function public.set_case_activities(uuid, jsonb) to authenticated;

-- ---------------------------------------------------------------- homologação: soma exata e atividades no snapshot
do $$
declare
  v_def text := pg_get_functiondef('public.rapido_blockers(uuid)'::regprocedure);
  v_new text;
begin
  v_new := replace(v_def,
    '  if not exists (select 1 from public.companies c where c.id = v.company_id and c.cnae_principal is not null) then',
    '  if exists (select 1 from public.case_activities a where a.case_id = p_case_id)
     and (select sum(a.percentual) from public.case_activities a where a.case_id = p_case_id) <> 100 then
    v_out := v_out || (''A soma dos percentuais das atividades é '' ||
      (select replace(to_char(sum(a.percentual), ''FM990.00''), ''.'', '','') from public.case_activities a where a.case_id = p_case_id) ||
      ''%, precisa ser exatamente 100,00%'');
  end if;
  if not exists (select 1 from public.companies c where c.id = v.company_id and c.cnae_principal is not null) then');
  if v_new = v_def then
    raise exception 'rapido_blockers: trecho esperado não encontrado';
  end if;
  execute v_new;

  v_def := pg_get_functiondef('public.homologate_case(uuid)'::regprocedure);
  v_new := replace(v_def,
    'from public.manual_values m where m.case_id = p_case_id), ''[]''::jsonb))',
    'from public.manual_values m where m.case_id = p_case_id), ''[]''::jsonb),
         ''activities'', coalesce((select jsonb_agg(jsonb_build_object(
            ''cnae'', a.cnae, ''descricao'', a.descricao, ''percentual'', a.percentual, ''origem'', a.origem)
            order by a.percentual desc, a.cnae)
          from public.case_activities a where a.case_id = p_case_id), ''[]''::jsonb))');
  if v_new = v_def then
    raise exception 'homologate_case: trecho esperado não encontrado';
  end if;
  execute v_new;
end;
$$;
