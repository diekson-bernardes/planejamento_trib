"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    const { error } = await createClient().auth.signInWithPassword({
      email: String(form.get("email")),
      password: String(form.get("password")),
    });
    setLoading(false);
    if (error) {
      setError("E-mail ou senha inválidos.");
      return;
    }
    router.replace("/cases");
    router.refresh();
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={onSubmit} className="card w-full max-w-sm space-y-4" aria-describedby="login-erro">
        <div>
          <h1>Entrar</h1>
          <p className="mt-1 text-sm text-slate-600">Importação e conciliação de documentos fiscais</p>
        </div>
        <div>
          <label className="label" htmlFor="email">E-mail</label>
          <input className="input" id="email" name="email" type="email" autoComplete="email" required />
        </div>
        <div>
          <label className="label" htmlFor="password">Senha</label>
          <input className="input" id="password" name="password" type="password" autoComplete="current-password" required />
        </div>
        {error && (
          <p id="login-erro" role="alert" className="alert-error">
            {error}
          </p>
        )}
        <button className="btn-primary w-full" type="submit" disabled={loading}>
          {loading ? "Entrando…" : "Entrar"}
        </button>
        <p className="text-xs text-slate-500">Acesso por convite do administrador do seu escritório.</p>
      </form>
    </main>
  );
}
