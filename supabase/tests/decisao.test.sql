-- Ciclo 3 — AT-211, AT-214 a AT-217, AT-219, AT-220: responsável técnico, limiar, fluxo de aprovação com
-- segregação, devolução com comentário, reset por premissa, recomendação emitida imutável, RLS e Storage.
begin;
create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(31);

-- ---------------------------------------------------------------- fixture (superusuário)
insert into public.tax_cases (id, office_id, company_id, period_start, period_end)
values ('d0000000-0000-4000-8000-0000000000d3', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2026-08-01', '2026-08-31');
insert into public.source_files (id, office_id, case_id, storage_path, original_name, sha256, uploaded_by)
values ('e0000000-0000-4000-8000-0000000000d3', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000d3',
        'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000d3/e0000000-0000-4000-8000-0000000000d3.pdf',
        'pgdas.pdf', repeat('d', 64), 'a2222222-2222-4222-8222-222222222222');
update public.source_files set status = 'extracted', competence = '2026-08-01'
 where id = 'e0000000-0000-4000-8000-0000000000d3';
update public.jobs set status = 'done' where payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000d3';
insert into public.assumptions (id, office_id, case_id, key, scope, grp, label, value_type, suggested_value,
                                suggested_origin, value, status)
values ('f3000000-0000-4000-8000-0000000000d3', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000d3', 'folha.rat', 'caso', 'folha', 'RAT', 'percent', '"0.02"',
        '{"source": "regra"}', '"0.02"', 'confirmed'),
       ('f4000000-0000-4000-8000-0000000000d3', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000d3', 'projecao.margem', 'competencia:2026-09', 'projecao', 'Margem',
        'ratio', '"0.1000"', '{"source": "snapshot"}', null, 'pending');

-- ---------------------------------------------------------------- administração (AT-214)
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

select throws_ok($$ select public.request_projection('d0000000-0000-4000-8000-0000000000d3') $$,
  'P0001', 'Planejamento exige dossiê homologado', 'projeção exige dossiê homologado');
select lives_ok($$ select * from public.homologate_case('d0000000-0000-4000-8000-0000000000d3') $$, 'homologa o dossiê');
select lives_ok($$ select public.request_projection('d0000000-0000-4000-8000-0000000000d3') $$,
  'projeção pedida mesmo com premissa pendente (prévia bloqueada no worker)');
select throws_ok(
  $$ select public.set_technical_responsible('a0000000-0000-4000-8000-000000000001', 'a2222222-2222-4222-8222-222222222222', true, 'Analista', 'SP-1') $$,
  '42501', null, 'analista não marca responsável técnico');
select throws_like($$ select public.confirm_assumption('f4000000-0000-4000-8000-0000000000d3', '"1.5"', 'margem impossível') $$,
  'Valor inválido para a premissa (ratio)', 'margem fora de −1..1 é recusada');
select lives_ok($$ select public.confirm_assumption('f4000000-0000-4000-8000-0000000000d3', '"-0.0500"', 'Prejuízo previsto no orçamento') $$,
  'margem negativa (prejuízo) é aceita com justificativa');

select set_config('request.jwt.claims', '{"sub": "a1111111-1111-4111-8111-111111111111", "role": "authenticated"}', true);
select throws_like(
  $$ select public.set_technical_responsible('a0000000-0000-4000-8000-000000000001', 'a1111111-1111-4111-8111-111111111111', true, 'Maria', null) $$,
  'Informe nome profissional e CRC%', 'responsável técnico exige nome e CRC');
select lives_ok(
  $$ select public.set_technical_responsible('a0000000-0000-4000-8000-000000000001', 'a1111111-1111-4111-8111-111111111111', true, 'Maria Contadora', 'sp-123456/o-7') $$,
  'admin marca a si mesmo como responsável técnico');
select is(public.is_technical_responsible('a0000000-0000-4000-8000-000000000001'), true, 'admin agora é responsável técnico');
select throws_ok($$ select public.set_decision_threshold('a0000000-0000-4000-8000-000000000001', 1.5) $$,
  'P0001', null, 'limiar fora de (0, 1) é recusado');
select lives_ok($$ select public.set_decision_threshold('a0000000-0000-4000-8000-000000000001', 0.08) $$, 'admin define o limiar');
select is(public.decision_threshold('a0000000-0000-4000-8000-000000000001'), 0.08::numeric, 'limiar do escritório gravado');
select is((select count(*) from public.audit_events where event in ('member.technical_responsible', 'office.decision_threshold')
            and office_id = 'a0000000-0000-4000-8000-000000000001' and created_at = now())::int, 2,
          'configurações auditadas');

-- ---------------------------------------------------------------- projeções e recomendações gravadas pelo worker
reset role;
insert into public.projections (id, office_id, case_id, snapshot_id, snapshot_sha256, assumptions_hash, rules_version,
                                rules_hash, decision_version, decision_hash, threshold, year, status, recommendation)
select p.id, s.office_id, s.case_id, s.id, s.sha256, p.h, '2026.1.0', repeat('2', 64), '2026.1.0', repeat('3', 64), 0.05,
       2026, 'done', jsonb_build_object('status', p.st)
  from public.snapshots s,
       (values ('ab000000-0000-4000-8000-0000000000d1'::uuid, repeat('a', 64), 'recomendado'),
               ('ab000000-0000-4000-8000-0000000000d2'::uuid, repeat('b', 64), 'bloqueado'),
               ('ab000000-0000-4000-8000-0000000000d3'::uuid, repeat('c', 64), 'inconclusivo')) p(id, h, st)
 where s.case_id = 'd0000000-0000-4000-8000-0000000000d3';
insert into public.recommendations (id, office_id, case_id, projection_id, computed_status, elaborated_by) values
  ('ac000000-0000-4000-8000-0000000000d1', 'a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000d3',
   'ab000000-0000-4000-8000-0000000000d1', 'recomendado', 'a2222222-2222-4222-8222-222222222222'),
  ('ac000000-0000-4000-8000-0000000000d2', 'a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000d3',
   'ab000000-0000-4000-8000-0000000000d2', 'bloqueado', 'a2222222-2222-4222-8222-222222222222'),
  ('ac000000-0000-4000-8000-0000000000d3', 'a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000d3',
   'ab000000-0000-4000-8000-0000000000d3', 'inconclusivo', 'a1111111-1111-4111-8111-111111111111');

-- ---------------------------------------------------------------- fluxo (AT-211, AT-215 a AT-217)
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "a1111111-1111-4111-8111-111111111111", "role": "authenticated"}', true);
select lives_ok($$ select public.submit_recommendation('ac000000-0000-4000-8000-0000000000d3') $$, 'RT envia a própria elaboração');
select throws_like($$ select public.approve_recommendation('ac000000-0000-4000-8000-0000000000d3') $$,
  'Quem elaborou não pode aprovar%', 'RT não aprova a própria elaboração');
select throws_like($$ select public.return_recommendation('ac000000-0000-4000-8000-0000000000d3', 'ok') $$,
  'Comentário obrigatório%', 'devolução exige comentário');
select lives_ok($$ select public.return_recommendation('ac000000-0000-4000-8000-0000000000d3', 'Revisar margem de setembro') $$,
  'devolução com comentário');
select is((select status || '|' || (select comment from public.recommendation_events
                                    where recommendation_id = r.id and event = 'returned')
             from public.recommendations r where id = 'ac000000-0000-4000-8000-0000000000d3'),
          'rascunho|Revisar margem de setembro', 'devolvida volta a rascunho com comentário registrado');

select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);
select throws_like($$ select public.submit_recommendation('ac000000-0000-4000-8000-0000000000d2') $$,
  'Recomendação bloqueada%', 'recomendação bloqueada não vai para revisão');
select lives_ok($$ select public.submit_recommendation('ac000000-0000-4000-8000-0000000000d1') $$, 'analista envia para revisão');
select throws_ok($$ select public.approve_recommendation('ac000000-0000-4000-8000-0000000000d1') $$,
  '42501', null, 'analista (não RT) não aprova');

select set_config('request.jwt.claims', '{"sub": "b3333333-3333-4333-8333-333333333333", "role": "authenticated"}', true);
select is((select count(*) from public.recommendations where case_id = 'd0000000-0000-4000-8000-0000000000d3')::int
          + (select count(*) from public.projections where case_id = 'd0000000-0000-4000-8000-0000000000d3')::int,
          0, 'B não vê projeções nem recomendações de A');
select throws_ok($$ select public.approve_recommendation('ac000000-0000-4000-8000-0000000000d1') $$,
  'P0002', null, 'B não aprova recomendação de A');
select is(public.decision_threshold('a0000000-0000-4000-8000-000000000001'), null, 'B não lê o limiar de A');

select set_config('request.jwt.claims', '{"sub": "a1111111-1111-4111-8111-111111111111", "role": "authenticated"}', true);
select lives_ok($$ select public.approve_recommendation('ac000000-0000-4000-8000-0000000000d1') $$, 'RT aprova a elaboração do analista');

-- AT-219: premissa alterada depois da aprovação → volta a rascunho
select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);
select lives_ok($$ select public.confirm_assumption('f3000000-0000-4000-8000-0000000000d3', '"0.03"', 'CNAE de risco grave') $$,
  'premissa alterada após aprovação');
select is((select status from public.recommendations where id = 'ac000000-0000-4000-8000-0000000000d1'), 'rascunho',
          'aprovada volta a rascunho quando a premissa muda');

-- regeneração de premissas (worker volta a premissa a pendente): recomendação em revisão volta a rascunho
select set_config('request.jwt.claims', '{"sub": "a1111111-1111-4111-8111-111111111111", "role": "authenticated"}', true);
select lives_ok($$ select public.submit_recommendation('ac000000-0000-4000-8000-0000000000d3') $$, 'reenviada para revisão');
reset role;
update public.assumptions set status = 'pending' where id = 'f3000000-0000-4000-8000-0000000000d3';
select is((select status from public.recommendations where id = 'ac000000-0000-4000-8000-0000000000d3'), 'rascunho',
          'premissa que volta a pendente devolve a recomendação para rascunho');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

-- ---------------------------------------------------------------- imutabilidade e Storage
select throws_ok(
  $$ insert into storage.objects (bucket_id, name, owner_id)
     values ('documents', 'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000d3/reports/x.pdf',
             'a2222222-2222-4222-8222-222222222222') $$,
  '42501', null, 'usuário não grava no caminho de relatórios');

reset role;
update public.recommendations set status = 'emitida', pdf_path = 'x', pdf_sha256 = repeat('e', 64)
 where id = 'ac000000-0000-4000-8000-0000000000d1';
select throws_like($$ update public.recommendations set pdf_sha256 = repeat('f', 64) where id = 'ac000000-0000-4000-8000-0000000000d1' $$,
  'Recomendação emitida é imutável', 'recomendação emitida é imutável');

select * from finish();
rollback;
