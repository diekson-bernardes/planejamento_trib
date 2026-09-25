-- Arquivos-fonte e fila de jobs do worker.

create table public.source_files (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  case_id uuid not null,
  storage_path text not null unique,
  original_name text,
  sha256 char(64) not null check (sha256 ~ '^[0-9a-f]{64}$'),
  size_bytes integer check (size_bytes >= 0),
  doc_type text check (doc_type in (
    'PGDAS_D', 'FOLHA_ALTERDATA', 'DRE_ALTERDATA', 'BALANCETE_ALTERDATA'
  )),
  cnpj char(14),
  competence date,
  status text not null default 'uploaded' check (status in (
    'uploaded', 'processing', 'extracted', 'failed', 'rejected', 'unclassified', 'cnpj_mismatch'
  )),
  error_code text,
  error_message text,
  parser_version text,
  result_hash text,
  pages integer,
  uploaded_by uuid not null default auth.uid() references auth.users (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (case_id, sha256),
  unique (id, office_id),
  foreign key (case_id, office_id) references public.tax_cases (id, office_id) on delete cascade,
  -- o objeto no Storage é sempre <escritório>/<dossiê>/<arquivo>.pdf: impede apontar para o PDF de outro dossiê
  constraint source_files_path_matches check (
    storage_path = office_id::text || '/' || case_id::text || '/' || id::text || '.pdf'
  )
);

create index source_files_case_idx on public.source_files (case_id);

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  office_id uuid not null references public.offices (id) on delete cascade,
  kind text not null check (kind in ('extract', 'reconcile', 'export_xlsx')),
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check (status in ('queued', 'running', 'done', 'failed')),
  attempts integer not null default 0,
  run_after timestamptz not null default now(),
  locked_at timestamptz,
  last_error text,
  idempotency_key text not null unique,
  created_at timestamptz not null default now(),
  finished_at timestamptz
);

create index jobs_claim_idx on public.jobs (status, run_after, created_at);

-- Enfileira de forma idempotente (mesma chave = mesmo job).
create or replace function public.enqueue_job(
  p_office uuid, p_kind text, p_payload jsonb, p_key text
) returns void
language sql
security definer
set search_path = public
as $$
  insert into public.jobs (office_id, kind, payload, idempotency_key)
  values (p_office, p_kind, p_payload, p_key)
  on conflict (idempotency_key) do nothing;
$$;

revoke all on function public.enqueue_job(uuid, text, jsonb, text) from public, anon, authenticated;
grant execute on function public.enqueue_job(uuid, text, jsonb, text) to service_role;

-- Novo arquivo → job de extração.
create or replace function public.tg_source_files_enqueue()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.enqueue_job(
    new.office_id, 'extract',
    jsonb_build_object('file_id', new.id, 'case_id', new.case_id),
    'extract:' || new.id || ':' || new.sha256
  );
  update public.tax_cases set status = 'processing'
   where id = new.case_id and status in ('draft', 'review');
  return new;
end;
$$;

create trigger source_files_enqueue
  after insert on public.source_files
  for each row execute function public.tg_source_files_enqueue();

-- Classificação manual de arquivo "não classificado" → reprocessa com o tipo escolhido.
-- Só vale para ações de usuário (auth.uid() presente); o worker grava o tipo detectado livremente.
create or replace function public.tg_source_files_reclassify()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.doc_type is distinct from old.doc_type and auth.uid() is not null then
    if old.status <> 'unclassified' then
      raise exception 'Somente arquivos não classificados podem ser reclassificados'
        using errcode = 'P0001';
    end if;
    new.status := 'uploaded';
    new.error_code := null;
    new.error_message := null;
    new.updated_at := now();
    perform public.enqueue_job(
      new.office_id, 'extract',
      jsonb_build_object('file_id', new.id, 'case_id', new.case_id, 'manual_doc_type', new.doc_type),
      'extract:' || new.id || ':' || new.sha256 || ':manual:' || new.doc_type
    );
  end if;
  return new;
end;
$$;

create trigger source_files_reclassify
  before update of doc_type on public.source_files
  for each row execute function public.tg_source_files_reclassify();

alter table public.source_files enable row level security;
alter table public.jobs enable row level security;

revoke all on table public.source_files from anon, authenticated;
revoke all on table public.jobs from anon, authenticated;
grant select, insert on table public.source_files to authenticated;
grant update (doc_type) on table public.source_files to authenticated;
grant select on table public.jobs to authenticated;

create policy source_files_select on public.source_files
  for select to authenticated using (public.is_member(office_id));
create policy source_files_insert on public.source_files
  for insert to authenticated
  with check (public.is_member(office_id) and uploaded_by = auth.uid() and status = 'uploaded');
create policy source_files_update on public.source_files
  for update to authenticated using (public.is_member(office_id)) with check (public.is_member(office_id));

create policy jobs_select on public.jobs
  for select to authenticated using (public.is_member(office_id));

-- Pedido de exportação XLSX pelo usuário (somente este tipo de job).
create or replace function public.request_xlsx_export(p_case_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_office uuid;
  v_snapshot uuid;
begin
  select c.office_id, s.id into v_office, v_snapshot
    from public.tax_cases c
    left join public.snapshots s on s.case_id = c.id
   where c.id = p_case_id;
  if v_office is null or not public.is_member(v_office) then
    raise exception 'Dossiê não encontrado' using errcode = 'P0002';
  end if;
  if v_snapshot is null then
    raise exception 'Dossiê ainda não homologado' using errcode = 'P0001';
  end if;
  -- Exportação que falhou pode ser pedida de novo (a chave idempotente impediria).
  update public.jobs
     set status = 'queued', attempts = 0, run_after = now(), last_error = null,
         finished_at = null, locked_at = null
   where idempotency_key = 'export_xlsx:' || v_snapshot and status = 'failed';
  if found then
    return;
  end if;
  perform public.enqueue_job(
    v_office, 'export_xlsx',
    jsonb_build_object('case_id', p_case_id, 'snapshot_id', v_snapshot),
    'export_xlsx:' || v_snapshot
  );
end;
$$;
