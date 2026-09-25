-- Dados locais de desenvolvimento e teste (fictícios). Nunca usar em produção.
-- Escritório A: admin + analista. Escritório B: analista (usado nos testes de isolamento).
-- Senha local de todos: senha-local-123

insert into public.offices (id, name, settings) values
  ('a0000000-0000-4000-8000-000000000001', 'Escritório A (teste)', '{"tolerance_brl": 1.00}'),
  ('b0000000-0000-4000-8000-000000000002', 'Escritório B (teste)', '{"tolerance_brl": 1.00}');

insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
  confirmation_token, recovery_token, email_change_token_new, email_change
)
select
  '00000000-0000-0000-0000-000000000000', u.id, 'authenticated', 'authenticated', u.email,
  extensions.crypt('senha-local-123', extensions.gen_salt('bf')), now(),
  '{"provider": "email", "providers": ["email"]}'::jsonb, '{}'::jsonb, now(), now(),
  '', '', '', ''
from (values
  ('a1111111-1111-4111-8111-111111111111'::uuid, 'admin.a@example.com'),
  ('a2222222-2222-4222-8222-222222222222'::uuid, 'analista.a@example.com'),
  ('b3333333-3333-4333-8333-333333333333'::uuid, 'analista.b@example.com')
) as u(id, email);

insert into auth.identities (id, user_id, provider_id, provider, identity_data, last_sign_in_at, created_at, updated_at)
select gen_random_uuid(), u.id, u.id::text, 'email',
       jsonb_build_object('sub', u.id::text, 'email', u.email, 'email_verified', true),
       now(), now(), now()
from auth.users u
where u.email in ('admin.a@example.com', 'analista.a@example.com', 'analista.b@example.com');

insert into public.office_members (office_id, user_id, role) values
  ('a0000000-0000-4000-8000-000000000001', 'a1111111-1111-4111-8111-111111111111', 'admin'),
  ('a0000000-0000-4000-8000-000000000001', 'a2222222-2222-4222-8222-222222222222', 'analyst'),
  ('b0000000-0000-4000-8000-000000000002', 'b3333333-3333-4333-8333-333333333333', 'analyst');

-- Empresa fictícia do escritório A.
insert into public.companies (id, office_id, cnpj, legal_name) values
  ('c0000000-0000-4000-8000-00000000000a', 'a0000000-0000-4000-8000-000000000001',
   '11222333000181', 'Comércio Exemplo Ltda (fictícia)');

-- Mapeamento padrão Alterdata (padrão do escritório: company_id nulo).
-- Códigos observados nas amostras: balancete usa o código reduzido; DRE usa a classificação.
insert into public.account_mappings (office_id, company_id, target, doc_type, account_code)
select o.id, null, m.target, m.doc_type, m.code
from public.offices o
cross join (values
  ('vendas',             'BALANCETE_ALTERDATA', '40101'),
  ('vendas',             'DRE_ALTERDATA',       '4.1.1.01.001'),
  ('simples_despesa',    'BALANCETE_ALTERDATA', '34009'),
  ('simples_despesa',    'DRE_ALTERDATA',       '3.1.1.15.009'),
  ('simples_a_recolher', 'BALANCETE_ALTERDATA', '20308'),
  ('inss_a_pagar',       'BALANCETE_ALTERDATA', '20403'),
  ('fgts_a_pagar',       'BALANCETE_ALTERDATA', '20405'),
  ('salarios_a_pagar',   'BALANCETE_ALTERDATA', '20401')
) as m(target, doc_type, code);
