import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client.js";
import InvoiceDetail from "./InvoiceDetail.jsx";
import StatusBadge from "./StatusBadge.jsx";
import { dateVN, FILE_TYPE, money, STATUS } from "./format.js";

// Danh sach hoa don + bo loc. `refreshKey` doi gia tri thi tai lai (trang tai len dung de bao co hoa don moi).
export default function InvoiceList({ refreshKey = 0, user }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [mine, setMine] = useState(false);   // chi hoa don do chinh toi tai len
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    const p = new URLSearchParams({ limit: "100" });
    if (q.trim()) p.set("q", q.trim());
    if (status) p.set("status", status);
    if (mine) p.set("mine", "true");
    return api(`/api/invoices?${p}`).then((r) => { setRows(r.data); setTotal(r.total); setErr(""); })
      .catch((e) => setErr(e.message));
  }, [q, status, mine]);

  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load, refreshKey]);

  // Co hoa don dang xu ly (OCR/LLM) thi 3 giay hoi lai mot lan
  const processing = rows.some((r) => r.status === "dang_xu_ly");
  useEffect(() => {
    if (!processing) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [processing, load]);

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm số HĐ, người bán, MST, tên file"
          className="w-72 rounded border p-2 text-sm" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded border p-2 text-sm">
          <option value="">Mọi trạng thái</option>
          {Object.entries(STATUS).map(([k, [label]]) => <option key={k} value={k}>{label}</option>)}
        </select>
        {user?.can_work && (
          <label className="flex items-center gap-1.5 text-sm">
            <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} /> Chỉ hóa đơn của tôi
          </label>
        )}
        <span className="ml-auto text-sm text-slate-500">{total} hóa đơn</span>
      </div>
      {err && <p className="mb-2 text-sm text-red-600">{err}</p>}
      <div className="overflow-x-auto rounded border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase text-slate-600">
            <tr>{["Tệp", "Loại", "Số HĐ", "Ngày", "Người bán", "MST", "Tổng tiền", "Trạng thái", "Phụ trách", ""].map((h) => (
              <th key={h} className="px-3 py-2 font-medium">{h}</th>))}</tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.invoice_id} className="border-t hover:bg-slate-50">
                <td className="max-w-[12rem] truncate px-3 py-2" title={r.filename}>{r.filename}</td>
                <td className="px-3 py-2">{FILE_TYPE[r.file_type]}</td>
                <td className="px-3 py-2">{r.invoice_number || "—"}</td>
                <td className="px-3 py-2">{dateVN(r.invoice_date)}</td>
                <td className="max-w-[14rem] truncate px-3 py-2" title={r.seller_name}>{r.seller_name || "—"}</td>
                <td className="px-3 py-2">{r.mst_seller || "—"}</td>
                <td className="px-3 py-2 text-right tabular-nums">{money(r.total_amount)}</td>
                <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                <td className="max-w-[10rem] truncate px-3 py-2" title={r.uploaded_by_name}>
                  {r.uploaded_by_name || "—"}{r.uploaded_by === user?.user_id && <span className="ml-1 text-xs text-blue-700">(bạn)</span>}
                </td>
                <td className="px-3 py-2"><button className="text-blue-700" onClick={() => setSelected(r.invoice_id)}>Xem</button></td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={10} className="px-3 py-8 text-center text-slate-500">Chưa có hóa đơn nào.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {selected && <InvoiceDetail invoiceId={selected} onClose={() => setSelected(null)} onChanged={load} />}
    </section>
  );
}
