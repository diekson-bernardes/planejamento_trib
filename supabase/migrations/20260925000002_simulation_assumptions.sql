-- Premissas usadas em cada simulação (cópia imutável, a mesma que gerou assumptions_hash).
-- A exportação da memória lê esta cópia, e não as premissas atuais do dossiê, que podem ter mudado depois.
-- Simulações anteriores a esta migration ficam com '[]' e a exportação avisa que a cópia não foi registrada.
alter table public.simulations
  add column assumptions jsonb not null default '[]'::jsonb;

comment on column public.simulations.assumptions is
  'Premissas confirmadas no momento do cálculo: [{key, scope, label, suggested_value, value, justification, confirmed_at}]';
