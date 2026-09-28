-- Ajustes de layout: administrador cria outro escritório e troca entre eles no topo da tela.
-- Quem cria vira administrador do novo escritório; configurações (tolerância, limiar) e o mapeamento de contas padrão
-- (company_id nulo) são copiados do escritório de origem, do qual o usuário precisa ser administrador.

create or replace function public.create_office(p_name text, p_copy_from uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_name text := trim(coalesce(p_name, ''));
  v_settings jsonb;
  v_id uuid;
begin
  if auth.uid() is null or not public.is_admin(p_copy_from) then
    raise exception 'Só o administrador do escritório atual cria um novo escritório' using errcode = '42501';
  end if;
  if length(v_name) < 3 then
    raise exception 'Informe o nome do escritório (mín. 3 caracteres)' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.offices o join public.office_members m on m.office_id = o.id
              where m.user_id = auth.uid() and lower(o.name) = lower(v_name)) then
    raise exception 'Você já participa de um escritório com esse nome' using errcode = 'P0001';
  end if;
  select settings into v_settings from public.offices where id = p_copy_from;
  insert into public.offices (name, settings) values (v_name, coalesce(v_settings, jsonb_build_object('tolerance_brl', 1.00)))
  returning id into v_id;
  insert into public.office_members (office_id, user_id, role) values (v_id, auth.uid(), 'admin');
  insert into public.account_mappings (office_id, company_id, target, doc_type, account_code)
  select v_id, null, target, doc_type, account_code
    from public.account_mappings where office_id = p_copy_from and company_id is null;
  perform public.write_audit(v_id, 'office.created', 'offices', v_id, null,
    jsonb_build_object('name', v_name, 'copied_from', p_copy_from));
  perform public.write_audit(p_copy_from, 'office.created', 'offices', v_id, null,
    jsonb_build_object('name', v_name, 'copied_from', p_copy_from));
  return v_id;
end;
$$;

revoke all on function public.create_office(text, uuid) from public, anon;
grant execute on function public.create_office(text, uuid) to authenticated;
