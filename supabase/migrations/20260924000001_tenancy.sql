-- Tenancy: escritórios, membros e funções de autorização usadas por todas as políticas RLS.
create extension if not exists pgcrypto with schema extensions;

create type public.member_role as enum ('admin', 'analyst');

create table public.offices (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(trim(name)) > 0),
  settings jsonb not null default jsonb_build_object('tolerance_brl', 1.00),
  created_at timestamptz not null default now(),
  constraint offices_tolerance_valid check (
    (settings ? 'tolerance_brl') and (settings ->> 'tolerance_brl')::numeric >= 0
  )
);

create table public.office_members (
  office_id uuid not null references public.offices (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role public.member_role not null default 'analyst',
  created_at timestamptz not null default now(),
  primary key (office_id, user_id)
);

create index office_members_user_idx on public.office_members (user_id);

-- security definer: consultada dentro das políticas sem recursão de RLS.
create or replace function public.is_member(p_office uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.office_members
    where office_id = p_office and user_id = auth.uid()
  );
$$;

create or replace function public.is_admin(p_office uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.office_members
    where office_id = p_office and user_id = auth.uid() and role = 'admin'
  );
$$;

revoke all on function public.is_member(uuid) from public, anon;
revoke all on function public.is_admin(uuid) from public, anon;
grant execute on function public.is_member(uuid) to authenticated, service_role;
grant execute on function public.is_admin(uuid) to authenticated, service_role;

alter table public.offices enable row level security;
alter table public.office_members enable row level security;

revoke all on table public.offices from anon, authenticated;
revoke all on table public.office_members from anon, authenticated;
grant select on table public.offices to authenticated;
grant update (settings) on table public.offices to authenticated;
grant select, insert, update, delete on table public.office_members to authenticated;

create policy offices_select on public.offices
  for select to authenticated using (public.is_member(id));
create policy offices_update on public.offices
  for update to authenticated using (public.is_admin(id)) with check (public.is_admin(id));

create policy office_members_select on public.office_members
  for select to authenticated using (public.is_member(office_id));
create policy office_members_insert on public.office_members
  for insert to authenticated with check (public.is_admin(office_id));
create policy office_members_update on public.office_members
  for update to authenticated using (public.is_admin(office_id)) with check (public.is_admin(office_id));
create policy office_members_delete on public.office_members
  for delete to authenticated using (public.is_admin(office_id) and user_id <> auth.uid());
