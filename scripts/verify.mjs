#!/usr/bin/env node
// Verify Gate do DEFINE (npm run verify): exit 0 somente se TODAS as etapas passarem.
// Pré-requisitos: Docker Desktop em execução, Supabase local (npm run db:start) e as amostras
// reais em SAMPLES_DIR (padrão docs/Amostras, fora do Git por conterem dados pessoais).
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const isWin = process.platform === "win32";
const python = process.env.PYTHON ?? (isWin ? "python" : "python3");

const SAMPLES = [
  "1.PGDASD-DECLARACAO-37704456202606001.pdf",
  "1.PGDASD-DECLARACAO-37704456202607001.pdf",
  "1.PGDASD-DECLARACAO-37704456202608001.pdf",
  "2.Resumo da Folha 08.pdf",
  "3.DRE 08.pdf",
  "4.Balancete 08.pdf",
];

function run(label, command, args, { quiet = false, env = {} } = {}) {
  process.stdout.write(`\n▶ ${label}\n`);
  const started = Date.now();
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: quiet ? "pipe" : "inherit",
    shell: isWin,
    env: { ...process.env, ...env },
  });
  const seconds = ((Date.now() - started) / 1000).toFixed(1);
  const ok = result.status === 0;
  process.stdout.write(`${ok ? "✔" : "✘"} ${label} (${seconds}s)\n`);
  return ok;
}

function fail(message) {
  process.stderr.write(`\n✘ Verify Gate: ${message}\n`);
  process.exit(1);
}

// 1. Pré-requisitos: falham explicitamente em vez de pular testes.
const samplesDirRaw = process.env.SAMPLES_DIR ?? "docs/Amostras";
const samplesDir = isAbsolute(samplesDirRaw) ? samplesDirRaw : join(root, samplesDirRaw);
const missing = SAMPLES.filter((name) => !existsSync(join(samplesDir, name)));
if (missing.length) fail(`amostras ausentes em ${samplesDir}: ${missing.join(", ")} (defina SAMPLES_DIR)`);

if (!run("Docker Engine ativo", "docker", ["info"], { quiet: true })) {
  fail("Docker Engine indisponível — abra o Docker Desktop.");
}
if (!run("Supabase local em execução", "npx", ["supabase", "status"], { quiet: true })) {
  fail("Supabase local parado — rode: npm run db:start");
}

// 2. Etapas do gate.
const steps = [
  ["Worker: pytest (golden, conciliação, pipeline, desempenho)", python,
    ["-m", "pytest", "services/worker/tests", "-q", "-p", "no:cacheprovider"],
    { env: { VERIFY_STRICT: "1", SAMPLES_DIR: samplesDir } }],
  ["Banco: pgTAP (RLS e homologação)", "npx", ["supabase", "test", "db"], {}],
  ["Web: typecheck", "npm", ["run", "typecheck", "--workspace", "apps/web"], {}],
  ["Web: vitest", "npm", ["run", "test", "--workspace", "apps/web"], {}],
];

const results = steps.map(([label, command, args, options]) => [label, run(label, command, args, options)]);

process.stdout.write("\n──────── Resumo do Verify Gate ────────\n");
for (const [label, ok] of results) process.stdout.write(`${ok ? "✔" : "✘"} ${label}\n`);
const allOk = results.every(([, ok]) => ok);
process.stdout.write(allOk ? "\nVERIFY GATE: PASS\n" : "\nVERIFY GATE: FAIL\n");
process.exit(allOk ? 0 : 1);
