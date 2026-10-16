import OwnerBadge from "./OwnerBadge.jsx";
// Trang giu cho: nguoi phu trach thay bang giao dien that (xem docs/PHAN_CONG.md)
export default function Placeholder({ title, pkg, tasks }) {
  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold">{title}</h1>
      <OwnerBadge pkg={pkg} />
      <p className="mt-3 text-sm text-slate-600">Chưa làm. Nhiệm vụ: {tasks}</p>
    </div>
  );
}
