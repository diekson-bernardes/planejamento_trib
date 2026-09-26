-- Ciclo 4 — Reforma 2027: Livro de Apuração como documento, R7, alvo compras_mercadorias, quarta alternativa,
-- premissas de 2027 que não bloqueiam o cálculo de 2026, projeção por exercício e Livro recusado após homologação.
begin;
create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(14);

-- ---------------------------------------------------------------- fixture (superusuário)
insert into public.tax_cases (id, office_id, company_id, period_start, period_end)
values ('d0000000-0000-4000-8000-0000000000e4', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2026-08-01', '2026-08-31');
insert into public.source_files (id, office_id, case_id, storage_path, original_name, sha256, uploaded_by)
values ('e0000000-0000-4000-8000-0000000000e4', 'a0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-0000000000e4',
        'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000e4/e0000000-0000-4000-8000-0000000000e4.pdf',
        'livro.pdf', repeat('e', 64), 'a2222222-2222-4222-8222-222222222222');

select lives_ok($$ update public.source_files set status = 'extracted', competence = '2026-08-01',
                    doc_type = 'LIVRO_ICMS_ALTERDATA' where id = 'e0000000-0000-4000-8000-0000000000e4' $$,
  'Livro de Apuração do ICMS é um tipo de documento aceito');
select lives_ok($$ insert into public.reconciliations (office_id, case_id, competence, rule, description, left_label,
                    right_label, tolerance, status)
                  values ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000e4', '2026-08-01',
                          'R7', 'Compras para comercialização', 'Livro', 'Balancete', 1, 'ok') $$,
  'regra R7 aceita na conciliação');
select is((select account_code from public.account_mappings
            where office_id = 'a0000000-0000-4000-8000-000000000001' and company_id is null
              and target = 'compras_mercadorias' and doc_type = 'BALANCETE_ALTERDATA'), '13101',
  'padrão do escritório: compras de mercadorias = 13101');

update public.jobs set status = 'done' where payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000e4';
insert into public.assumptions (office_id, case_id, key, scope, grp, label, value_type, suggested_value,
                                suggested_origin, value, status)
values ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000e4', 'folha.rat', 'caso', 'folha',
        'RAT', 'percent', '"0.02"', '{"source": "regra"}', '"0.02"', 'confirmed'),
       ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000e4', 'reforma.cbs_aliquota', 'caso',
        'reforma_2027', 'Alíquota da CBS em 2027', 'ratio', null, '{"source": "escritorio"}', null, 'pending');

-- ---------------------------------------------------------------- como analista
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

select lives_ok($$ select * from public.homologate_case('d0000000-0000-4000-8000-0000000000e4') $$, 'homologa o dossiê');
select throws_ok($$ insert into public.source_files (office_id, case_id, storage_path, original_name, sha256, uploaded_by)
                    values ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000e4',
                            'a0000000-0000-4000-8000-000000000001/d0000000-0000-4000-8000-0000000000e4/x.pdf',
                            'livro-tardio.pdf', repeat('f', 64), 'a2222222-2222-4222-8222-222222222222') $$,
  null, null, 'Livro enviado depois da homologação é recusado');
select lives_ok($$ select public.request_calculation('d0000000-0000-4000-8000-0000000000e4') $$,
  'premissa pendente do grupo reforma_2027 não bloqueia o cálculo de 2026');
select is((select count(*) from public.jobs where kind = 'calculate'
            and payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000e4')::int, 1, 'cálculo de 2026 enfileirado');
select lives_ok($$ select public.request_projection('d0000000-0000-4000-8000-0000000000e4', 2027) $$,
  'projeção de 2027 pedida (o worker bloqueia a recomendação enquanto houver alíquota pendente)');
select is((select (payload ->> 'year')::int from public.jobs where kind = 'project'
            and payload ->> 'case_id' = 'd0000000-0000-4000-8000-0000000000e4'), 2027, 'job de projeção leva o exercício');
select throws_like($$ select public.request_projection('d0000000-0000-4000-8000-0000000000e4', 2030) $$,
  'Exercício 2030 sem regras parametrizadas', 'exercício sem regras é recusado');

reset role;
select ok((select pg_get_constraintdef(oid) from pg_constraint where conname = 'simulation_lines_regime_check')
          like '%SIMPLES_HIBRIDO%', 'simulation_lines aceita o regime SIMPLES_HIBRIDO');
select ok((select pg_get_constraintdef(oid) from pg_constraint where conname = 'projection_lines_regime_check')
          like '%SIMPLES_HIBRIDO%', 'projection_lines aceita o regime SIMPLES_HIBRIDO');

-- premissa da Reforma confirmada: devolve a rascunho só a recomendação de 2027; a de 2026 aprovada fica
insert into public.projections (id, office_id, case_id, snapshot_id, snapshot_sha256, assumptions_hash, rules_version,
                                rules_hash, decision_version, decision_hash, threshold, year, status, recommendation)
select p.id, s.office_id, s.case_id, s.id, s.sha256, repeat('a', 64), p.v, md5(p.v) || md5(p.v), p.v, repeat('3', 64), 0.05,
       p.y, 'done', '{"status": "recomendado"}'
  from public.snapshots s,
       (values ('ab000000-0000-4000-8000-0000000000e6'::uuid, 2026, '2026.1.0'),
               ('ab000000-0000-4000-8000-0000000000e7'::uuid, 2027, '2027.1.0')) p(id, y, v)
 where s.case_id = 'd0000000-0000-4000-8000-0000000000e4';
insert into public.recommendations (id, office_id, case_id, projection_id, computed_status, elaborated_by, status,
                                    approved_by, approved_at)
select ('ac' || substr(p::text, 3))::uuid, 'a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000e4',
       p, 'recomendado', 'a2222222-2222-4222-8222-222222222222', 'aprovada', 'a1111111-1111-4111-8111-111111111111', now()
  from unnest(array['ab000000-0000-4000-8000-0000000000e6', 'ab000000-0000-4000-8000-0000000000e7']::uuid[]) p;
update public.assumptions set value = '"0.095"', status = 'confirmed'
 where case_id = 'd0000000-0000-4000-8000-0000000000e4' and key = 'reforma.cbs_aliquota';
select is((select status from public.recommendations where projection_id = 'ab000000-0000-4000-8000-0000000000e6'),
  'aprovada', 'premissa de 2027 não devolve a recomendação de 2026');
select is((select status from public.recommendations where projection_id = 'ab000000-0000-4000-8000-0000000000e7'),
  'rascunho', 'premissa de 2027 devolve a recomendação de 2027 a rascunho');

select * from finish();
rollback;
