import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../api/client.js";
import StatusBadge from "../invoices/StatusBadge.jsx";
import { dateVN, money } from "../invoices/format.js";

// Chon hoa don de lam viec (dung chung cho man hinh Kiem tra va Dinh khoan). Chon xong dat ?id=... tren URL.
// Cac the loc: "Tat ca" dung dau, roi 3 trang thai chinh (hoa don bi tu choi chi hien o "Tat ca").
const TABS = [
  ["all", "Tất cả", null],
  ["cho_xac_nhan", "Chờ xác nhận", "cho_xac_nhan"],
  ["cho_duyet", "Chờ duyệt", "cho_duyet"],
  ["da_duyet", "Đã duyệt", "da_duyet"],
];

export default function InvoicePicker({ title, hint }) {
  const [, setParams] = useSearchParams();
  const [rows, setRows] = useState(null);
  const [tab, setTab] = useState("all");
  const [err, setErr] = useState("");

  useEffect(() => {
    api("/api/invoices?limit=200").then((r) => setRows(r.data)).catch((e) => setErr(e.message));
  }, []);

  const open = (id) => setParams({ id: String(id) });
  const count = (st) => (rows || []).filter((r) => !st || r.status === st).length;
  const cur = TABS.find((t) => t[0] === tab);
  const shown = (rows || []).filter((r) => !cur[2] || r.status === cur[2]);

  return (
    <section className="mx-auto max-w-6xl">
      <h2 className="mb-2 text-2xl font-bold text-slate-800">{title}</h2>
      <p className="mb-4 text-sm text-slate-600">{hint}</p>

      <div className="mb-5 flex flex-wrap items-center gap-3 text-sm" role="tablist">
        {TABS.map(([k, label, st]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`rounded-full px-5 py-2 ${tab === k ? "bg-blue-600 font-semibold text-white shadow-sm" : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"}`}>
            {label}{rows ? ` (${count(st)})` : ""}
          </button>
        ))}
      </div>

      {err && <p className="mb-3 text-sm text-red-600">{err}</p>}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow">
        <table className="min-w-[40rem] divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase text-slate-600">
            <tr>{["#", "Số HĐ", "Ngày", "Người bán", "Tổng tiền", "Trạng thái", ""].map((h) => (
              <th key={h} className="px-6 py-3 font-semibold">{h}</th>))}</tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {shown.map((r) => (
              <tr key={r.invoice_id} className="cursor-pointer border-t transition-colors hover:bg-blue-50" onClick={() => open(r.invoice_id)}>
                <td className="px-6 py-4 text-slate-500">{r.invoice_id}</td>
                <td className="px-6 py-4 font-medium">{r.invoice_number || "—"}</td>
                <td className="px-6 py-4">{dateVN(r.invoice_date)}</td>
                <td className="max-w-[24rem] truncate px-6 py-4 font-medium" title={r.seller_name}>{r.seller_name || "—"}</td>
                <td className="px-6 py-4 text-right font-medium tabular-nums">{money(r.total_amount)}</td>
                <td className="px-6 py-4"><StatusBadge status={r.status} /></td>
                <td className="px-6 py-4 text-right">
                  <button onClick={(e) => { e.stopPropagation(); open(r.invoice_id); }}
                    className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white shadow hover:bg-blue-700">Mở</button>
                </td>
              </tr>
            ))}
            {rows && shown.length === 0 && (
              <tr><td colSpan={7} className="px-6 py-12 text-center text-sm text-slate-500">
                {tab === "all" ? "Chưa có hóa đơn nào." : `Không có hóa đơn nào ở mục “${cur[1]}”.`}
              </td></tr>
            )}
            {!rows && !err && <tr><td colSpan={7} className="px-6 py-12 text-center text-sm text-slate-500">Đang tải…</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
