import "server-only";

import { createClient } from "@supabase/supabase-js";

import type { Database } from "@/lib/database.types";

/**
 * Cliente com a chave de serviço (ignora RLS). Uso restrito a operações de Auth do Admin
 * do escritório (convite e e-mails dos membros), sempre depois de checar is_admin.
 */
/** E-mail por id de usuário, percorrendo todas as páginas do Auth (sem N+1). */
export async function listUserEmails(): Promise<Map<string, string>> {
  const admin = createAdminClient();
  const emails = new Map<string, string>();
  const perPage = 1000;
  for (let page = 1; ; page += 1) {
    const { data, error } = await admin.auth.admin.listUsers({ page, perPage });
    if (error || !data) break;
    data.users.forEach((u) => u.email && emails.set(u.id, u.email.toLowerCase()));
    if (data.users.length < perPage) break;
  }
  return emails;
}

export function createAdminClient() {
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!key) throw new Error("SUPABASE_SERVICE_ROLE_KEY não configurada");
  return createClient<Database>(process.env.NEXT_PUBLIC_SUPABASE_URL!, key, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}
