const OWNERS = { A: "Hiển", B: "Khánh", C: "Dương" };
export default function OwnerBadge({ pkg }) {
  return <span className="rounded bg-slate-200 px-2 py-0.5 text-xs">Gói {pkg} · {OWNERS[pkg]}</span>;
}
