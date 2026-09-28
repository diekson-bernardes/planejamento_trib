-- Novo escritório: só administrador cria; quem cria vira admin; mapeamento padrão e configurações copiados; os demais
-- membros do escritório de origem não entram no novo.
begin;
create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(8);

set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);
select throws_ok($$ select public.create_office('Escritório do analista', 'a0000000-0000-4000-8000-000000000001') $$,
  '42501', null, 'analista não cria escritório');

select set_config('request.jwt.claims', '{"sub": "a1111111-1111-4111-8111-111111111111", "role": "authenticated"}', true);
select throws_like($$ select public.create_office('ab', 'a0000000-0000-4000-8000-000000000001') $$,
  'Informe o nome do escritório%', 'nome curto recusado');
select lives_ok($$ select public.create_office('Escritório Santarém (teste)', 'a0000000-0000-4000-8000-000000000001') $$,
  'administrador cria escritório');
select throws_like($$ select public.create_office('escritório santarém (TESTE)', 'a0000000-0000-4000-8000-000000000001') $$,
  'Você já participa de um escritório com esse nome', 'nome repetido recusado');

select is((select m.role::text from public.office_members m join public.offices o on o.id = m.office_id
            where o.name = 'Escritório Santarém (teste)' and m.user_id = 'a1111111-1111-4111-8111-111111111111'),
  'admin', 'quem cria é administrador do novo escritório');
select is((select count(*) from public.account_mappings am join public.offices o on o.id = am.office_id
            where o.name = 'Escritório Santarém (teste)')::int,
  (select count(*) from public.account_mappings where office_id = 'a0000000-0000-4000-8000-000000000001' and company_id is null)::int,
  'mapeamento padrão copiado');

select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);
select is((select count(*) from public.offices where name = 'Escritório Santarém (teste)')::int, 0,
  'analista do escritório de origem não vê o novo escritório');
select is((select count(*) from public.tax_cases t join public.offices o on o.id = t.office_id
            where o.name = 'Escritório Santarém (teste)')::int, 0, 'novo escritório começa sem dossiês');

select * from finish();
rollback;
