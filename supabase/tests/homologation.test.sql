-- AT-009, AT-017, AT-019, AT-020: ajuste com motivo e auditoria, bloqueio por divergência,
-- snapshot com hash e imutabilidade do dossiê homologado.
begin;
create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(19);

-- ---------------------------------------------------------------- fixture (superusuário)
insert into public.tax_cases (id, office_id, company_id, period_start, period_end)
values ('d0000000-0000-4000-8000-0000000000b1', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2026-08-01', '2026-08-31');

insert into public.source_files (id, office_id, case_id, storage_path, original_name, sha256, uploaded_by)
values ('e0000000-0000-4000-8000-0000000000b1', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000b1',
        'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000b1/e0000000-0000-4000-8000-0000000000b1.pdf',
        'pgdas.pdf', repeat('b', 64), 'a2222222-2222-4222-8222-222222222222');

update public.source_files
   set status = 'extracted', doc_type = null, competence = '2026-08-01', parser_version = 'test'
 where id = 'e0000000-0000-4000-8000-0000000000b1';

insert into public.extracted_values (id, office_id, case_id, file_id, ordinal, doc_type, competence, section,
                                     field_key, label, value, page, bbox, parser_version)
values ('f0000000-0000-4000-8000-0000000000b1', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000b1', 'e0000000-0000-4000-8000-0000000000b1', 0, 'PGDAS_D',
        '2026-08-01', '2.1', 'rpa_total', 'Receita Bruta do PA', 1000.00, 1, array[0, 0, 10, 10], 'test');

insert into public.reconciliations (id, office_id, case_id, competence, rule, description, left_label,
                                    left_value, right_label, right_value, diff, tolerance, status)
values ('90000000-0000-4000-8000-0000000000b1', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000b1', '2026-08-01', 'R1', 'Receita', 'PGDAS', 1000,
        'DRE', 990, 10, 1, 'divergent');

-- ---------------------------------------------------------------- como analista do escritório A
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

-- AT-017: ajuste exige motivo e preserva o original
select throws_ok(
  $$ insert into public.value_adjustments (value_id, new_value, reason)
     values ('f0000000-0000-4000-8000-0000000000b1', 995, 'ok') $$,
  '23514', null, 'ajuste com motivo curto é rejeitado');

select lives_ok(
  $$ insert into public.value_adjustments (value_id, new_value, reason)
     values ('f0000000-0000-4000-8000-0000000000b1', 995, 'Correção conforme DRE revisada') $$,
  'ajuste com motivo é aceito');

select is((select value from public.extracted_values where id = 'f0000000-0000-4000-8000-0000000000b1'),
          1000.00::numeric, 'valor original preservado');
select is((select effective_value from public.effective_values where id = 'f0000000-0000-4000-8000-0000000000b1'),
          995.00::numeric, 'valor efetivo = ajuste');
select is((select old_value from public.value_adjustments where value_id = 'f0000000-0000-4000-8000-0000000000b1'),
          1000.00::numeric, 'valor anterior registrado');
select is((select author from public.value_adjustments where value_id = 'f0000000-0000-4000-8000-0000000000b1'),
          'a2222222-2222-4222-8222-222222222222'::uuid, 'autor registrado');
select is((select count(*) from public.audit_events
            where event = 'value.adjusted' and entity_id = 'f0000000-0000-4000-8000-0000000000b1')::int,
          1, 'ajuste auditado');
select is((select count(*) from public.jobs
            where kind = 'reconcile' and payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000b1')::int,
          1, 'ajuste enfileira reconciliação');

-- AT-009: divergência sem justificativa bloqueia
select throws_like(
  $$ select * from public.homologate_case('d0000000-0000-4000-8000-0000000000b1') $$,
  'Homologação bloqueada:%R1 08/2026%', 'divergência sem justificativa bloqueia a homologação');

select throws_ok(
  $$ update public.reconciliations set justification = 'x'
      where id = '90000000-0000-4000-8000-0000000000b1' $$,
  'P0001', null, 'justificativa curta é rejeitada');

update public.reconciliations
   set justification = 'Diferença de devoluções lançadas em setembro'
 where id = '90000000-0000-4000-8000-0000000000b1';

-- Conciliação na fila (ajuste acima) também bloqueia: o snapshot não pode usar resultado desatualizado.
select throws_like(
  $$ select * from public.homologate_case('d0000000-0000-4000-8000-0000000000b1') $$,
  'Homologação bloqueada:%em andamento%', 'job de conciliação pendente bloqueia a homologação');

-- worker concluiu os jobs do dossiê
reset role;
update public.jobs set status = 'done' where payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000b1';

-- mudança de tolerância reenfileira a conciliação dos dossiês abertos
update public.offices set settings = '{"tolerance_brl": 2.00}' where id = 'a0000000-0000-4000-8000-000000000001';
select is((select count(*) from public.jobs
            where kind = 'reconcile' and status = 'queued' and idempotency_key like '%:tolerance:%'
              and payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000b1')::int,
          1, 'mudança de tolerância reenfileira a conciliação');
update public.jobs set status = 'done' where payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000b1';

set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

-- AT-019: homologação gera snapshot com hash
select lives_ok(
  $$ select * from public.homologate_case('d0000000-0000-4000-8000-0000000000b1') $$,
  'homologa após justificar');

select is((select status from public.tax_cases where id = 'd0000000-0000-4000-8000-0000000000b1'),
          'homologated', 'dossiê homologado');
select is((select sha256 from public.snapshots where case_id = 'd0000000-0000-4000-8000-0000000000b1'),
          (select encode(extensions.digest(content::text, 'sha256'), 'hex')::char(64)
             from public.snapshots where case_id = 'd0000000-0000-4000-8000-0000000000b1'),
          'hash do snapshot confere com o conteúdo');
select is((select jsonb_array_length(content -> 'values') from public.snapshots
            where case_id = 'd0000000-0000-4000-8000-0000000000b1'),
          1, 'snapshot contém os valores efetivos');

-- AT-020: dossiê homologado é somente leitura
select throws_like(
  $$ insert into public.value_adjustments (value_id, new_value, reason)
     values ('f0000000-0000-4000-8000-0000000000b1', 1, 'tentativa após homologar') $$,
  'Dossiê homologado%', 'ajuste bloqueado após homologação');

select throws_like(
  $$ update public.reconciliations set justification = 'nova justificativa qualquer'
      where id = '90000000-0000-4000-8000-0000000000b1' $$,
  'Dossiê homologado%', 'justificativa bloqueada após homologação');

reset role;
select throws_like(
  $$ update public.snapshots set sha256 = repeat('0', 64)
      where case_id = 'd0000000-0000-4000-8000-0000000000b1' $$,
  '%append-only%', 'snapshot imutável até para o superusuário');

select * from finish();
rollback;
