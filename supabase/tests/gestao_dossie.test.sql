-- Gestão do dossiê: excluir/editar/reabrir por qualquer membro do escritório, nunca por outro escritório; a liberação
-- das proteções só vale dentro das funções (usuário não apaga dados protegidos direto, mesmo marcando a transação).
begin;
create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(14);

-- ---------------------------------------------------------------- fixture (superusuário)
insert into public.companies (id, office_id, cnpj, legal_name)
values ('c0000000-0000-4000-8000-0000000000c7', 'a0000000-0000-4000-8000-000000000001', '99887766000105', 'Empresa sem dossiê');
insert into public.tax_cases (id, office_id, company_id, period_start, period_end, kind)
values ('d0000000-0000-4000-8000-0000000000c7', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2026-06-01', '2026-08-31', 'completo');
insert into public.source_files (id, office_id, case_id, storage_path, original_name, sha256, uploaded_by)
values ('e0000000-0000-4000-8000-0000000000c7', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000c7',
        'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000c7/e0000000-0000-4000-8000-0000000000c7.pdf',
        'errado.pdf', repeat('c', 64), 'a2222222-2222-4222-8222-222222222222');

-- ---------------------------------------------------------------- escritório B não mexe no dossiê de A
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "b3333333-3333-4333-8333-333333333333", "role": "authenticated"}', true);
select throws_ok($$ select public.delete_case('d0000000-0000-4000-8000-0000000000c7', 'tentativa indevida') $$,
  'P0002', 'Dossiê não encontrado', 'outro escritório não exclui o dossiê');
select throws_ok($$ select public.update_case('d0000000-0000-4000-8000-0000000000c7', '2026-01-01', '2026-03-31', 'completo') $$,
  'P0002', 'Dossiê não encontrado', 'outro escritório não edita o dossiê');
select throws_ok($$ select public.delete_source_file('e0000000-0000-4000-8000-0000000000c7') $$,
  'P0002', 'Arquivo não encontrado', 'outro escritório não exclui arquivo');
select throws_ok($$ select public.delete_company('c0000000-0000-4000-8000-0000000000c7') $$,
  'P0002', 'Empresa não encontrada', 'outro escritório não exclui empresa');

-- ---------------------------------------------------------------- analista de A
select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);
select set_config('app.purge_case', 'd0000000-0000-4000-8000-0000000000c7', true);
select throws_ok($$ delete from public.source_files where id = 'e0000000-0000-4000-8000-0000000000c7' $$,
  '42501', null, 'marcar a transação não dá DELETE direto em source_files');
select throws_ok($$ delete from public.audit_events $$, '42501', null, 'auditoria continua sem DELETE');
select set_config('app.purge_case', '', true);

select throws_like($$ select public.delete_case('d0000000-0000-4000-8000-0000000000c7', 'x') $$,
  'Informe o motivo%', 'excluir exige motivo');
select throws_like($$ select public.reopen_case('d0000000-0000-4000-8000-0000000000c7', 'motivo válido') $$,
  'Dossiê não está homologado', 'reabrir só dossiê homologado');
select throws_like($$ select public.update_company('c0000000-0000-4000-8000-0000000000c7', ' ') $$,
  'Informe a razão social', 'razão social vazia recusada');
select lives_ok($$ select public.update_case('d0000000-0000-4000-8000-0000000000c7', '2026-05-15', '2026-08-10', 'completo') $$,
  'analista edita o período');
select is((select period_start::text || ' ' || period_end::text from public.tax_cases where id = 'd0000000-0000-4000-8000-0000000000c7'),
  '2026-05-01 2026-08-31', 'período normalizado para meses inteiros');
select lives_ok($$ select public.delete_source_file('e0000000-0000-4000-8000-0000000000c7') $$, 'analista exclui arquivo');
select lives_ok($$ select public.delete_company('c0000000-0000-4000-8000-0000000000c7') $$, 'empresa sem dossiê excluída');
select lives_ok($$ select public.delete_case('d0000000-0000-4000-8000-0000000000c7', 'Criado por engano no teste') $$,
  'analista exclui o dossiê');

select * from finish();
rollback;
