-- Bucket privado de documentos e políticas por escritório (primeiro segmento do path).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('documents', 'documents', false, 20971520,
        array['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'])
on conflict (id) do nothing;

-- Evita erro de cast quando o path não começa com um UUID.
create or replace function public.storage_path_office(p_name text)
returns uuid
language plpgsql
immutable
as $$
declare
  v_first text := split_part(p_name, '/', 1);
begin
  if v_first ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    return v_first::uuid;
  end if;
  return null;
end;
$$;

-- Usuários leem e enviam; não alteram nem apagam (imutabilidade dos originais).
create policy documents_select on storage.objects
  for select to authenticated
  using (bucket_id = 'documents' and public.is_member(public.storage_path_office(name)));

create policy documents_insert on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'documents'
    and public.is_member(public.storage_path_office(name))
    and name not like '%/exports/%'
  );
