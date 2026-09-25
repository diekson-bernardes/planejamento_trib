import { STATUS, type Tone } from "@/lib/format";

const TONE_CLASS: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
  info: "bg-sky-50 text-sky-800 ring-sky-200",
  success: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  warning: "bg-amber-50 text-amber-900 ring-amber-200",
  danger: "bg-red-50 text-red-800 ring-red-200",
};

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const info = STATUS[status] ?? { label: status, tone: "neutral" as Tone };
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONE_CLASS[info.tone]}`}
    >
      {label ?? info.label}
    </span>
  );
}
