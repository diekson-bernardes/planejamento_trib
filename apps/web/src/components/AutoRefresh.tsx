"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** Recarrega os dados da página (router.refresh) enquanto houver processamento em andamento no worker — extração,
 *  consulta de CNAE, premissas, cálculo, projeção ou emissão do PDF. Para sozinho quando `active` fica falso. */
export function AutoRefresh({ active, intervalMs = 3000, label = "Processando… a página atualiza sozinha." }: {
  active: boolean;
  intervalMs?: number;
  label?: string;
}) {
  const router = useRouter();
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs, router]);
  if (!active) return null;
  return (
    <p role="status" aria-live="polite" className="alert-warning flex items-center gap-2">
      <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" aria-hidden />
      {label}
    </p>
  );
}
