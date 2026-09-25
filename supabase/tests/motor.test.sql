-- Ciclo 2 — AT-102, AT-104, AT-105, AT-124: planejamento só com dossiê homologado, justificativa obrigatória,
-- tipo do valor da premissa, bloqueio por premissa pendente, isolamento entre escritórios e imutabilidade da simulação.
begin;
create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(22);

-- ---------------------------------------------------------------- fixture (superusuário)
insert into public.tax_cases (id, office_id, company_id, period_start, period_end)
values ('d0000000-0000-4000-8000-0000000000c1', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2026-08-01', '2026-08-31');

insert into public.source_files (id, office_id, case_id, storage_path, original_name, sha256, uploaded_by)
values ('e0000000-0000-4000-8000-0000000000c1', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000c1',
        'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000c1/e0000000-0000-4000-8000-0000000000c1.pdf',
        'pgdas.pdf', repeat('c', 64), 'a2222222-2222-4222-8222-222222222222');
update public.source_files set status = 'extracted', competence = '2026-08-01'
 where id = 'e0000000-0000-4000-8000-0000000000c1';
update public.jobs set status = 'done' where payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000c1';

-- ---------------------------------------------------------------- como analista do escritório A
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

select throws_ok(
  $$ select public.request_planning('d0000000-0000-4000-8000-0000000000c1') $$,
  'P0001', 'Planejamento exige dossiê homologado', 'planejamento recusado antes da homologação');

select lives_ok($$ select * from public.homologate_case('d0000000-0000-4000-8000-0000000000c1') $$, 'homologa o dossiê');
select lives_ok($$ select public.request_planning('d0000000-0000-4000-8000-0000000000c1') $$, 'inicia o planejamento');
select is((select count(*) from public.jobs where kind = 'suggest_assumptions'
            and payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000c1')::int, 1, 'job de sugestões enfileirado');

-- worker grava as sugestões (superusuário)
reset role;
insert into public.assumptions (id, office_id, case_id, key, scope, grp, label, value_type, suggested_value, suggested_origin)
values
  ('f1000000-0000-4000-8000-0000000000c1', 'a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000c1',
   'folha.rat', 'caso', 'folha', 'RAT', 'percent', '"0.02"', '{"source": "regra"}'),
  ('f2000000-0000-4000-8000-0000000000c1', 'a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000c1',
   'real.adicoes', 'competencia:2026-08', 'real', 'Adições', 'decimal', '"0.00"', '{"source": "padrao"}');
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

select is((select count(*) from public.assumptions where case_id = 'd0000000-0000-4000-8000-0000000000c1')::int,
          2, 'membro vê as premissas do escritório');

select throws_like(
  $$ select public.request_calculation('d0000000-0000-4000-8000-0000000000c1') $$,
  'Premissas pendentes de confirmação:%RAT%', 'cálculo bloqueado com premissa pendente');

select throws_like(
  $$ select public.confirm_assumption('f2000000-0000-4000-8000-0000000000c1', '"dez"', 'valor digitado errado') $$,
  'Valor inválido para a premissa (decimal)', 'decimal não numérico é recusado');
select throws_like(
  $$ select public.confirm_assumption('f1000000-0000-4000-8000-0000000000c1', '"2"', 'RAT em pontos percentuais') $$,
  'Valor inválido para a premissa (percent)', 'percentual acima de 1 (fração) é recusado');
select is(public.assumption_value_ok('taxes', null, '["icms", "xyz"]'), false, 'tributo desconhecido é recusado');
select is(public.assumption_value_ok('choice', '["nao", "sim", "nao_informado"]', '"talvez"'), false,
          'resposta fora das opções é recusada');
select is(public.assumption_value_ok('profile', '[{"anexos": ["I"]}, {"presumido": ["comercio"]}]',
                                     '{"anexo": "III", "presumido": "comercio", "fator_r": true}'), true,
          'perfil de atividade válido é aceito');

select throws_like(
  $$ select public.confirm_assumption('f1000000-0000-4000-8000-0000000000c1', '"0.03"', null) $$,
  'Justificativa obrigatória%', 'alterar sugestão sem justificativa é recusado');

select lives_ok(
  $$ select public.confirm_assumption('f1000000-0000-4000-8000-0000000000c1', '"0.03"', 'CNAE de risco grave') $$,
  'alterar sugestão com justificativa é aceito');

select lives_ok(
  $$ select public.confirm_assumption('f2000000-0000-4000-8000-0000000000c1', '"0.00"', null) $$,
  'confirmar o valor sugerido dispensa justificativa');

select is((select status || '|' || (value #>> '{}') || '|' || justification from public.assumptions
            where id = 'f1000000-0000-4000-8000-0000000000c1'),
          'confirmed|0.03|CNAE de risco grave', 'premissa confirmada com valor e justificativa');
select is((select count(*) from public.audit_events where event = 'assumption.confirmed'
            and entity_id = 'f1000000-0000-4000-8000-0000000000c1')::int, 1, 'confirmação auditada');

select lives_ok($$ select public.request_calculation('d0000000-0000-4000-8000-0000000000c1') $$,
  'cálculo enfileirado com todas as premissas confirmadas');

select throws_ok(
  $$ insert into public.simulations (office_id, case_id, snapshot_id, snapshot_sha256, assumptions_hash, rules_version,
                                     rules_hash, status)
     select office_id, case_id, id, sha256, repeat('0', 64), 'x', repeat('0', 64), 'done'
       from public.snapshots where case_id = 'd0000000-0000-4000-8000-0000000000c1' $$,
  '42501', null, 'usuário não grava simulação diretamente');

select throws_ok(
  $$ insert into storage.objects (bucket_id, name, owner_id)
     values ('documents', 'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000c1/simulations/x.xlsx',
             'a2222222-2222-4222-8222-222222222222') $$,
  '42501', null, 'usuário não grava no caminho de simulações do Storage');

-- ---------------------------------------------------------------- como analista do escritório B
select set_config('request.jwt.claims',
  '{"sub": "b3333333-3333-4333-8333-333333333333", "role": "authenticated"}', true);

select is((select count(*) from public.assumptions where case_id = 'd0000000-0000-4000-8000-0000000000c1')::int,
          0, 'B não vê premissas de A');
select throws_ok(
  $$ select public.confirm_assumption('f2000000-0000-4000-8000-0000000000c1', '"1.00"', 'tentativa indevida') $$,
  'P0002', null, 'B não confirma premissa de A');

-- ---------------------------------------------------------------- imutabilidade (superusuário)
reset role;
insert into public.simulations (id, office_id, case_id, snapshot_id, snapshot_sha256, assumptions_hash, rules_version,
                                rules_hash, status)
select 'aa000000-0000-4000-8000-0000000000c1', office_id, case_id, id, sha256, repeat('1', 64), '2026.1.0',
       repeat('2', 64), 'done'
  from public.snapshots where case_id = 'd0000000-0000-4000-8000-0000000000c1';

select throws_like(
  $$ update public.simulations set status = 'failed' where id = 'aa000000-0000-4000-8000-0000000000c1' $$,
  '%append-only%', 'simulação gravada é imutável');

select * from finish();
rollback;
