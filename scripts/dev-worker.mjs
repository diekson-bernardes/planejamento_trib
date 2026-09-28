#!/usr/bin/env node
// npm run dev:worker — sobe o worker local (extração de PDFs, cálculos, projeções, PDFs e consulta de CNAE).
// Não exige `pip install -e services/worker`: aponta o PYTHONPATH para services/worker/src. As configurações vêm do
// .env da raiz (carregado pelo próprio worker) ou de variáveis de ambiente já definidas.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { delimiter, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const python = process.env.PYTHON ?? (process.platform === "win32" ? "python" : "python3");
const src = join(root, "services", "worker", "src");
if (!existsSync(join(root, ".env"))) {
  process.stderr.write("Aviso: .env não encontrado na raiz — copie .env.example e preencha com `npx supabase status`.\n");
}
const env = {
  ...process.env,
  PYTHONPATH: [src, process.env.PYTHONPATH].filter(Boolean).join(delimiter),
  PYTHONIOENCODING: "utf-8",
};
const child = spawn(python, ["-m", "worker.main"], { cwd: root, env, stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));
