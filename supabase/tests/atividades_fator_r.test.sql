-- Ciclo 6 — atividades do planejamento rápido: gravação pela RPC, soma exata de 100,00%, CNAE inválido/repetido,
-- lista vazia, atividade única = 100%, bloqueio da homologação, snapshot com as atividades, trava pós-homologação e RLS.
begin;
create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;
-- fixture própria (desfeita no rollback): o teste não depende da empresa do seed, que pode ser excluída pela tela
insert into public.companies (id, office_id, cnpj, legal_name)
values ('c0000000-0000-4000-8000-00000000000a', 'a0000000-0000-4000-8000-000000000001', '11222333000181',
        'Comércio Exemplo Ltda (fictícia)')
on conflict do nothing;

select plan(19);

insert into public.tax_cases (id, office_id, company_id, period_start, period_end, kind)
values ('d0000000-0000-4000-8000-0000000000a6', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2025-09-01', '2026-08-31', 'rapido'),
       ('d0000000-0000-4000-8000-0000000000a7', 'a0000000-0000-4000-8000-000000000001',
        'c0000000-0000-4000-8000-00000000000a', '2026-08-01', '2026-08-31', 'completo');
update public.companies set cnae_principal = '4744001', razao_social_pendente = false
 where id = 'c0000000-0000-4000-8000-00000000000a';

-- ---------------------------------------------------------------- analista do escritório A
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "a2222222-2222-4222-8222-222222222222", "role": "authenticated"}', true);

select throws_ok($$ insert into public.case_activities (office_id, case_id, cnae, percentual)
                    values ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-0000000000a6', '4744001', 100) $$,
  '42501', null, 'escrita direta em case_activities é negada (só pela RPC)');
select throws_like($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6', '[]') $$,
  'Marque ao menos uma atividade%', 'lista vazia recusada');
select throws_like($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6',
                    '[{"cnae": "47440", "percentual": "100"}]') $$, 'CNAE inválido%', 'CNAE incompleto recusado');
select throws_like($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6',
                    '[{"cnae": "4744001", "percentual": "50"}, {"cnae": "4744-0/01", "percentual": "50"}]') $$,
  'CNAE repetido%', 'CNAE repetido recusado');
select throws_like($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6',
                    '[{"cnae": "4744001", "percentual": "60"}, {"cnae": "6201501", "percentual": "39.99"}]') $$,
  'A soma dos percentuais é 99,99%%%', 'soma 99,99% recusada');
select throws_like($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6',
                    '[{"cnae": "4744001", "percentual": "60"}, {"cnae": "6201501"}]') $$,
  'Informe o percentual de cada atividade%', 'percentual ausente recusado');
select throws_like($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a7',
                    '[{"cnae": "4744001", "percentual": "100"}]') $$,
  'Atividades só no planejamento rápido', 'dossiê completo não aceita atividades');

select lives_ok($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6',
                    '[{"cnae": "6201501", "descricao": "Desenvolvimento de software", "origem": "receita"}]') $$,
  'uma atividade sem percentual é aceita');
select is((select percentual from public.case_activities where case_id = 'd0000000-0000-4000-8000-0000000000a6'),
  100.00::numeric(5, 2), 'atividade única recebe 100%');

select lives_ok($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6',
                    '[{"cnae": "4744-0/01", "descricao": "Ferragens", "percentual": "60", "origem": "receita"},
                      {"cnae": "6201501", "descricao": "Software", "percentual": "40.00", "origem": "manual"}]') $$,
  'duas atividades somando 100,00% gravadas');
select is((select string_agg(cnae || '=' || percentual, ',' order by cnae) from public.case_activities
            where case_id = 'd0000000-0000-4000-8000-0000000000a6'),
  '4744001=60.00,6201501=40.00', 'conjunto substituído, CNAE normalizado');

-- ---------------------------------------------------------------- soma divergente gravada por fora bloqueia a homologação
reset role;
select is((select count(*) from public.audit_events where event = 'case_activities.set'
            and entity_id = 'd0000000-0000-4000-8000-0000000000a6')::int, 2, 'auditoria de cada gravação');
update public.case_activities set percentual = 30
 where case_id = 'd0000000-0000-4000-8000-0000000000a6' and cnae = '6201501';
set local role authenticated;
select ok(public.rapido_blockers('d0000000-0000-4000-8000-0000000000a6')
            @> array['A soma dos percentuais das atividades é 90,00%, precisa ser exatamente 100,00%'],
  'soma diferente de 100% bloqueia a homologação');
select lives_ok($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6',
                    '[{"cnae": "4744001", "percentual": "60"}, {"cnae": "6201501", "percentual": "40"}]') $$,
  'soma corrigida');

-- ---------------------------------------------------------------- homologação leva as atividades ao snapshot
select lives_ok($$ select public.enter_manual_values('d0000000-0000-4000-8000-0000000000a6', 'FATURAMENTO', m::date,
                    '{"faturamento.mes": "100000.00"}')
                  from generate_series('2025-09-01'::date, '2026-08-01'::date, interval '1 month') m $$,
  '12 meses de faturamento digitados');
select public.enter_manual_values('d0000000-0000-4000-8000-0000000000a6', 'FOLHA', '2026-08-01', '{"folha.salarios": "20000.00"}');
select public.enter_manual_values('d0000000-0000-4000-8000-0000000000a6', 'DRE', '2026-08-01', '{"dre.resultado": "9000.00"}');
select public.homologate_case('d0000000-0000-4000-8000-0000000000a6');
select is((select content -> 'activities' -> 1 ->> 'cnae' from public.snapshots
            where case_id = 'd0000000-0000-4000-8000-0000000000a6'),
  '6201501', 'snapshot contém as atividades (maior percentual primeiro)');

select throws_like($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6',
                    '[{"cnae": "4744001", "percentual": "100"}]') $$,
  'Dossiê homologado%', 'atividades travadas no dossiê homologado');

-- ---------------------------------------------------------------- escritório B
select set_config('request.jwt.claims', '{"sub": "b3333333-3333-4333-8333-333333333333", "role": "authenticated"}', true);
select is((select count(*) from public.case_activities where case_id = 'd0000000-0000-4000-8000-0000000000a6')::int, 0,
  'RLS: outro escritório não vê as atividades');
select throws_ok($$ select public.set_case_activities('d0000000-0000-4000-8000-0000000000a6',
                    '[{"cnae": "4744001", "percentual": "100"}]') $$,
  '42501', 'Dossiê não encontrado', 'outro escritório não grava atividades');

select * from finish();
rollback;
