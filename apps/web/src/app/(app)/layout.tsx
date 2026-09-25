import Link from "next/link";

import { selectOffice, signOut } from "@/app/(app)/cases/actions";
import { getSessionContext } from "@/lib/supabase/server";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, memberships, office } = await getSessionContext();

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <nav className="flex items-center gap-5 text-sm" aria-label="Principal">
            <Link href="/cases" className="font-semibold text-brand-700">Planejamento Tributário</Link>
            <Link href="/cases" className="text-slate-700 hover:text-slate-900">Dossiês</Link>
            {office?.role === "admin" && (
              <Link href="/admin" className="text-slate-700 hover:text-slate-900">Administração</Link>
            )}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            {memberships.length > 1 ? (
              <form action={selectOffice} className="flex items-center gap-2">
                <label htmlFor="officeId" className="sr-only">Escritório</label>
                <select id="officeId" name="officeId" defaultValue={office?.office_id} className="input py-1">
                  {memberships.map((m) => (
                    <option key={m.office_id} value={m.office_id}>{m.office_name}</option>
                  ))}
                </select>
                <button className="btn-secondary py-1" type="submit">Trocar</button>
              </form>
            ) : (
              <span className="text-slate-600">{office?.office_name}</span>
            )}
            <span className="hidden text-slate-500 sm:inline">{user.email}</span>
            <form action={signOut}>
              <button className="btn-secondary py-1" type="submit">Sair</button>
            </form>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        {office ? children : (
          <p className="alert-warning">Seu usuário ainda não pertence a nenhum escritório. Peça acesso ao administrador.</p>
        )}
      </main>
    </div>
  );
}
