import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../api/client.js";
import StatusBadge from "../invoices/StatusBadge.jsx";
import { dateVN, money } from "../invoices/format.js";

// Chon hoa don de lam viec (dung chung cho man hinh Kiem tra va Dinh khoan). Chon xong dat ?id=... tren URL.
const NEEDS_WORK = ["cho_xac_nhan", "tu_choi"];

export default function InvoicePicker({ title, hint }) {
  const [, setParams] = useSearchParams();
  const [rows, setRows] = useState(null);
  const [all, setAll] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api("/api/invoices?limit=200").then((r) => setRows(r.data)).catch((e) => setErr(e.message));
  }, []);

  const shown = (rows || []).filter((r) => all || NEEDS_WORK.includes(r.status));
  return (
    <section>
      <h1 className="mb-1 text-xl font-semibold">{title}</h1>
      <p className="mb-3 text-sm text-slate-600">{hint}</p>
      <div className="mb-3 flex gap-2 text-sm" role="tablist">
        {[[false, "Cần xử lý"], [true, "Tất cả"]].map(([v, label]) => (
          <button key={label} role="tab" aria-selected={all === v} onClick={() => setAll(v)}
            className={`rounded px-3 py-1 ${all === v ? "bg-blue-100 font-semibold text-blue-800 ring-1 ring-blue-300" : "text-blue-700 hover:bg-slate-100"}`}>
            {label}
          </button>
        ))}
      </div>
      {err && <p className="mb-2 text-sm text-red-600">{err}</p>}
      <div className="overflow-x-auto rounded border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase text-slate-600">
            <tr>{["#", "Số HĐ", "Ngày", "Người bán", "Tổng tiền", "Trạng thái", ""].map((h) => (
              <th key={h} className="px-3 py-2 font-medium">{h}</th>))}</tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.invoice_id} className="border-t hover:bg-slate-50">
                <td className="px-3 py-2">{r.invoice_id}</td>
                <td className="px-3 py-2">{r.invoice_number || "—"}</td>
                <td className="px-3 py-2">{dateVN(r.invoice_date)}</td>
                <td className="max-w-[18rem] truncate px-3 py-2" title={r.seller_name}>{r.seller_name || "—"}</td>
                <td className="px-3 py-2 text-right tabular-nums">{money(r.total_amount)}</td>
                <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                <td className="px-3 py-2">
                  <button className="text-blue-700" onClick={() => setParams({ id: String(r.invoice_id) })}>Mở</button>
                </td>
              </tr>
            ))}
            {rows && shown.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500">
                {all ? "Chưa có hóa đơn nào." : "Không có hóa đơn nào cần xử lý. Chọn “Tất cả” để xem lại các hóa đơn khác."}
              </td></tr>
            )}
            {!rows && !err && <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500">Đang tải…</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
