import "server-only";

import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { Database } from "@/lib/database.types";

export const OFFICE_COOKIE = "office_id";

/** Cliente com o JWT do usuário: toda consulta passa pela RLS. */
export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
          } catch {
            // Chamado de Server Component: o middleware renova a sessão.
          }
        },
      },
    },
  );
}

export type Membership = {
  office_id: string;
  role: "admin" | "analyst";
  office_name: string;
};

/** Usuário autenticado, escritórios dos quais é membro e o escritório ativo. */
export async function getSessionContext() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data } = await supabase
    .from("office_members")
    .select("office_id, role, offices(name)")
    .eq("user_id", user.id);

  const memberships: Membership[] = (data ?? []).map((m) => ({
    office_id: m.office_id,
    role: m.role,
    office_name: (m.offices as { name: string } | null)?.name ?? "Escritório",
  }));

  const cookieStore = await cookies();
  const selected = cookieStore.get(OFFICE_COOKIE)?.value;
  const office = memberships.find((m) => m.office_id === selected) ?? memberships[0] ?? null;

  return { supabase, user, memberships, office };
}
