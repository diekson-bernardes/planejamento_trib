-- AT-018: um usuário não lê nem grava dados/arquivos de outro escritório.
begin;
create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(22);

-- ---------------------------------------------------------------- fixture (superusuário)
insert into public.tax_cases (id, office_id, company_id, period_start, period_end)
values ('d0000000-0000-4000-8000-0000000000a1', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2026-06-01', '2026-08-31');

insert into public.source_files (id, office_id, case_id, storage_path, original_name, sha256, uploaded_by)
values ('e0000000-0000-4000-8000-0000000000a1', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000a1',
        'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000a1/e0000000-0000-4000-8000-0000000000a1.pdf',
        'teste.pdf', repeat('a', 64), 'a2222222-2222-4222-8222-222222222222');

insert into public.extracted_values (id, office_id, case_id, file_id, ordinal, doc_type, competence, section,
                                     field_key, label, value, page, bbox, parser_version)
values ('f0000000-0000-4000-8000-0000000000a1', 'a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000a1',
        'e0000000-0000-4000-8000-0000000000a1', 0, 'PGDAS_D', '2026-08-01', '2.1', 'rpa_total',
        'Receita Bruta do PA', 1000.00, 1, array[0, 0, 10, 10], 'test');

insert into public.validations (office_id, case_id, file_id, rule, status)
values ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000a1',
        'e0000000-0000-4000-8000-0000000000a1', 'pgdas.soma_atividades', 'pass');

insert into public.reconciliations (office_id, case_id, competence, rule, description, left_label,
                                    left_value, right_label, right_value, diff, tolerance, status)
values ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000a1', '2026-08-01',
        'R1', 'Receita', 'PGDAS', 1000, 'DRE', 1000, 0, 1, 'ok');

insert into storage.objects (bucket_id, name, owner_id)
values ('documents',
        'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000a1/e0000000-0000-4000-8000-0000000000a1.pdf',
        'a2222222-2222-4222-8222-222222222222');

-- ---------------------------------------------------------------- como analista do escritório B
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub": "b3333333-3333-4333-8333-333333333333", "role": "authenticated"}', true);

select is((select count(*) from public.offices where id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê o escritório A');
select is((select count(*) from public.office_members where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê membros de A');
select is((select count(*) from public.companies where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê empresas de A');
select is((select count(*) from public.tax_cases where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê dossiês de A');
select is((select count(*) from public.account_mappings where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê mapeamentos de A');
select is((select count(*) from public.source_files where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê arquivos de A');
select is((select count(*) from public.jobs where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê jobs de A');
select is((select count(*) from public.extracted_values where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê valores de A');
select is((select count(*) from public.effective_values where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê valores efetivos de A');
select is((select count(*) from public.validations where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê validações de A');
select is((select count(*) from public.reconciliations where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê conciliações de A');
select is((select count(*) from public.audit_events where office_id = 'a0000000-0000-4000-8000-000000000001')::int, 0, 'B não vê auditoria de A');
select is((select count(*) from storage.objects where name like 'a0000000-0000-4000-8000-000000000001/%')::int, 0, 'B não vê objetos de A no Storage');

select throws_ok(
  $$ insert into public.companies (office_id, cnpj, legal_name)
     values ('a0000000-0000-4000-8000-000000000001', '99888777000100', 'Invasora') $$,
  '42501', null, 'B não cria empresa em A');

select throws_ok(
  $$ insert into public.value_adjustments (value_id, new_value, reason)
     values ('f0000000-0000-4000-8000-0000000000a1', 1, 'tentativa indevida') $$,
  '42501', null, 'B não ajusta valor de A');

select throws_ok(
  $$ insert into storage.objects (bucket_id, name, owner_id)
     values ('documents', 'a0000000-0000-4000-8000-000000000001/x/invasao.pdf', 'b3333333-3333-4333-8333-333333333333') $$,
  '42501', null, 'B não envia arquivo para o path de A');

select throws_ok(
  $$ select * from public.homologate_case('d0000000-0000-4000-8000-0000000000a1') $$,
  'P0002', null, 'B não homologa dossiê de A');
-- ---------------------------------------------------------------- como analista do escritório A
select set_config('request.jwt.claims',
  '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

select is((select count(*) from public.tax_cases where id = 'd0000000-0000-4000-8000-0000000000a1')::int, 1, 'A vê o próprio dossiê');
select is((select count(*) from public.extracted_values where case_id = 'd0000000-0000-4000-8000-0000000000a1')::int, 1, 'A vê os próprios valores');
select is((select count(*) from storage.objects where name like 'a0000000-0000-4000-8000-000000000001/%')::int, 1, 'A vê o próprio objeto no Storage');
select is((select count(*) from public.companies where office_id = 'b0000000-0000-4000-8000-000000000002')::int, 0, 'A não vê empresas de B');

update public.offices set settings = '{"tolerance_brl": 5}' where id = 'a0000000-0000-4000-8000-000000000001';

select is((select (settings ->> 'tolerance_brl')::numeric from public.offices where id = 'a0000000-0000-4000-8000-000000000001'), 1.00, 'tolerância inalterada pelo analista');

select * from finish();
rollback;
