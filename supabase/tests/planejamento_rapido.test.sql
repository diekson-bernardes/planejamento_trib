-- Ciclo 5 — Planejamento Rápido: tipo do dossiê, valores digitados (RLS, validação, imutabilidade), CNAE digitado e
-- consultado, bloqueios de homologação e projeção só de 2027.
begin;
create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(20);

-- ---------------------------------------------------------------- fixture (superusuário)
insert into public.tax_cases (id, office_id, company_id, period_start, period_end, kind)
values ('d0000000-0000-4000-8000-0000000000f5', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2025-09-01', '2026-08-31', 'rapido'),
       ('d0000000-0000-4000-8000-0000000000f6', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2026-08-01', '2026-08-31', 'completo');
update public.companies set cnae_principal = null where id = 'c0000000-0000-4000-8000-00000000000a';

select throws_ok($$ insert into public.tax_cases (office_id, company_id, period_start, period_end, kind)
                    values ('a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-00000000000a',
                            '2026-01-01', '2026-12-31', 'outro') $$,
  '23514', null, 'tipo de dossiê desconhecido é recusado');

-- ---------------------------------------------------------------- como analista do escritório A
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

select throws_ok($$ insert into public.manual_values (office_id, case_id, doc_type, competence, field_key, value)
                    values ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000f5',
                            'FOLHA', '2026-08-01', 'folha.salarios', 1) $$,
  '42501', null, 'escrita direta em manual_values é negada (só pela RPC)');
select lives_ok($$ select public.enter_manual_values('d0000000-0000-4000-8000-0000000000f5', 'FATURAMENTO', '2026-08-15',
                    '{"faturamento.mes": "203180.77"}') $$, 'digita faturamento de um mês (normaliza para o dia 1º)');
select is((select value from public.manual_values where case_id = 'd0000000-0000-4000-8000-0000000000f5'
            and competence = '2026-08-01'), 203180.77::numeric(15, 2), 'valor digitado gravado');
select is((select entered_by::text from public.manual_values where case_id = 'd0000000-0000-4000-8000-0000000000f5' limit 1),
  'a2222222-2222-4222-8222-222222222222', 'autor da digitação registrado');
select throws_like($$ select public.enter_manual_values('d0000000-0000-4000-8000-0000000000f5', 'FOLHA', '2026-08-01',
                    '{"folha.salarios": "-1"}') $$, 'Valor inválido em folha.salarios%', 'valor negativo recusado');
select lives_ok($$ select public.enter_manual_values('d0000000-0000-4000-8000-0000000000f5', 'DRE', '2026-08-01',
                    '{"dre.resultado": "-500.00"}') $$, 'resultado da DRE aceita prejuízo');
select throws_like($$ select public.enter_manual_values('d0000000-0000-4000-8000-0000000000f5', 'FOLHA', '2026-08-01',
                    '{"dre.resultado": "1"}') $$, 'Campos válidos para FOLHA%', 'campo de outro documento recusado');
select throws_like($$ select public.enter_manual_values('d0000000-0000-4000-8000-0000000000f5', 'FOLHA', '2024-01-01',
                    '{"folha.salarios": "1"}') $$, 'Competência fora do período%', 'competência fora do período recusada');
select throws_like($$ select public.enter_manual_values('d0000000-0000-4000-8000-0000000000f6', 'FOLHA', '2026-08-01',
                    '{"folha.salarios": "1"}') $$, 'Digitação de valores só no planejamento rápido', 'dossiê completo não aceita digitação');

select throws_like($$ select * from public.homologate_case('d0000000-0000-4000-8000-0000000000f5') $$,
  '%Faturamento ausente: 09/2025%', 'homologação bloqueada sem os 12 meses de faturamento');
select ok(public.rapido_blockers('d0000000-0000-4000-8000-0000000000f5') @> array['Informe o CNAE principal da empresa (consulta à Receita ou digitação)'],
  'CNAE ausente bloqueia a homologação');

select throws_like($$ select public.set_company_cnae('c0000000-0000-4000-8000-00000000000a', '47440', null) $$,
  'CNAE deve ter 7 dígitos%', 'CNAE incompleto recusado');
select lives_ok($$ select public.set_company_cnae('c0000000-0000-4000-8000-00000000000a', '4744-0/01', 'Ferragens') $$,
  'CNAE digitado');
select is((select cnae_principal || '/' || cnae_origem from public.companies where id = 'c0000000-0000-4000-8000-00000000000a'),
  '4744001/manual', 'CNAE normalizado com origem manual');
select lives_ok($$ select public.request_company_lookup('c0000000-0000-4000-8000-00000000000a') $$, 'consulta de CNAE pedida');
select is((select count(*) from public.jobs where kind = 'lookup_company'
            and payload ->> 'company_id' = 'c0000000-0000-4000-8000-00000000000a')::int, 1, 'job lookup_company enfileirado');
select throws_like($$ select public.request_company_lookup('c0000000-0000-4000-8000-00000000000a') $$,
  'Consulta do CNAE já em andamento%', 'segunda consulta com a primeira na fila é recusada');

-- ---------------------------------------------------------------- escritório B não vê os valores digitados de A
select set_config('request.jwt.claims', '{"sub": "b3333333-3333-4333-8333-333333333333", "role": "authenticated"}', true);
select is((select count(*) from public.manual_values where case_id = 'd0000000-0000-4000-8000-0000000000f5')::int, 0,
  'RLS: outro escritório não vê valores digitados');

select throws_ok($$ select public.rapido_blockers('d0000000-0000-4000-8000-0000000000f5') $$,
  'P0002', 'Dossiê não encontrado', 'outro escritório não consulta os bloqueios do dossiê');

select * from finish();
rollback;
