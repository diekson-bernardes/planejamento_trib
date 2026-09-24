"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { registerUpload } from "@/app/(app)/cases/actions";
import { sha256Hex } from "@/lib/hash";
import { MAX_UPLOAD_BYTES } from "@/lib/schemas";
import { createClient } from "@/lib/supabase/client";

type Item = { name: string; state: "hash" | "upload" | "done" | "duplicate" | "error"; message?: string };

const STATE_LABEL: Record<Item["state"], string> = {
  hash: "Calculando hash…",
  upload: "Enviando…",
  done: "Enviado — na fila de processamento",
  duplicate: "Arquivo já enviado neste dossiê (mesmo conteúdo)",
  error: "Erro",
};

export function UploadDropzone({
  caseId,
  officeId,
  disabled,
  processing,
}: {
  caseId: string;
  officeId: string;
  disabled?: boolean;
  processing?: boolean;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

  // Enquanto houver arquivos em processamento, atualiza a página a cada 3 s.
  useEffect(() => {
    if (!processing) return;
    const id = setInterval(() => router.refresh(), 3000);
    return () => clearInterval(id);
  }, [processing, router]);

  function update(index: number, patch: Partial<Item>) {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...patch } : it)));
  }

  async function handleFiles(fileList: FileList | null) {
    if (!fileList?.length || disabled) return;
    const files = Array.from(fileList);
    const base = items.length;
    setItems((prev) => [...prev, ...files.map((f) => ({ name: f.name, state: "hash" as const }))]);
    setBusy(true);
    const supabase = createClient();

    for (const [offset, file] of files.entries()) {
      const index = base + offset;
      if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
        update(index, { state: "error", message: "Somente PDF é aceito." });
        continue;
      }
      if (file.size > MAX_UPLOAD_BYTES) {
        update(index, { state: "error", message: "Arquivo acima de 20 MB." });
        continue;
      }
      try {
        const sha256 = await sha256Hex(file);
        const { data: existing } = await supabase
          .from("source_files")
          .select("id")
          .eq("case_id", caseId)
          .eq("sha256", sha256)
          .maybeSingle();
        if (existing) {
          update(index, { state: "duplicate" });
          continue;
        }
        update(index, { state: "upload" });
        const fileId = crypto.randomUUID();
        const storagePath = `${officeId}/${caseId}/${fileId}.pdf`;
        const { error: upErr } = await supabase.storage
          .from("documents")
          .upload(storagePath, file, { contentType: "application/pdf", upsert: false });
        if (upErr) {
          update(index, { state: "error", message: "Falha no envio ao armazenamento." });
          continue;
        }
        const result = await registerUpload({
          caseId,
          fileId,
          storagePath,
          sha256,
          originalName: file.name,
          sizeBytes: file.size,
        });
        if (!result.ok) update(index, { state: "error", message: result.error });
        else update(index, { state: result.duplicate ? "duplicate" : "done" });
      } catch {
        update(index, { state: "error", message: "Erro inesperado no envio." });
      }
    }
    setBusy(false);
    router.refresh();
  }

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && !disabled && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void handleFiles(e.dataTransfer.files);
        }}
        className={`rounded-lg border-2 border-dashed p-6 text-center text-sm transition ${
          disabled
            ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
            : dragging
              ? "cursor-pointer border-brand-600 bg-brand-50 text-brand-900"
              : "cursor-pointer border-slate-300 bg-white text-slate-600 hover:border-brand-600"
        }`}
      >
        <p className="font-medium">
          {disabled ? "Dossiê homologado — envio bloqueado" : "Arraste os PDFs aqui ou clique para selecionar"}
        </p>
        <p className="mt-1 text-xs">PGDAS-D e relatórios Alterdata (folha, DRE, balancete) · PDF com texto · até 20 MB</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          onChange={(e) => {
            void handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>
      {items.length > 0 && (
        <ul className="space-y-1 text-sm" aria-live="polite">
          {items.map((it, i) => (
            <li key={i} className="flex items-center justify-between gap-3 rounded border border-slate-100 bg-white px-3 py-1.5">
              <span className="truncate">{it.name}</span>
              <span className={it.state === "error" ? "text-red-700" : it.state === "duplicate" ? "text-amber-800" : "text-slate-600"}>
                {it.message ?? STATE_LABEL[it.state]}
              </span>
            </li>
          ))}
        </ul>
      )}
      {busy && <p className="text-xs text-slate-500">Não feche a página até o envio terminar.</p>}
    </div>
  );
}
