import { STATUS } from "./format.js";

export default function StatusBadge({ status }) {
  const [label, cls] = STATUS[status] || [status, "bg-slate-100 text-slate-700"];
  return <span className={`rounded px-2 py-0.5 text-xs font-medium ${cls}`}>{label}</span>;
}
