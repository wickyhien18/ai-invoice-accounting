import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../api/client.js";
import StatusBadge from "../invoices/StatusBadge.jsx";
import { dateVN, money } from "../invoices/format.js";
import { isKTV, useUser } from "../../userContext.js";

// ---------------------------------------------------------
// COMPONENT PHÂN TRANG DÙNG CHUNG
// ---------------------------------------------------------
const Pagination = ({ totalItems, pageSize, currentPage, setPageSize, setCurrentPage }) => {
  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  return (
    <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
      <div className="flex items-center gap-3 text-sm text-slate-600 font-medium">
        <span>Hiển thị</span>
        <select 
          value={pageSize} 
          onChange={(e) => { 
            setPageSize(Number(e.target.value)); 
            setCurrentPage(1); 
          }}
          className="border border-slate-300 rounded px-2 py-1 bg-white focus:outline-none focus:border-blue-500 shadow-sm"
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
        </select>
        <span>dòng / trang</span>
      </div>
      
      <div className="flex items-center gap-4 text-sm font-medium">
        <span className="text-slate-500">
          Hiển thị {Math.min((currentPage - 1) * pageSize + 1, totalItems)} - {Math.min(currentPage * pageSize, totalItems)} trong tổng số {totalItems} dòng
        </span>
        
        <div className="flex items-center gap-2">
          <button 
            disabled={currentPage === 1} 
            onClick={() => setCurrentPage(p => p - 1)}
            className="px-3 py-1.5 border border-slate-300 rounded bg-white text-slate-700 hover:bg-slate-100 disabled:opacity-50 disabled:bg-slate-50 shadow-sm transition-colors"
          >
            Trước
          </button>
          <div className="px-4 py-1.5 bg-slate-200 text-slate-800 rounded font-bold">
            Trang {currentPage} / {totalPages}
          </div>
          <button 
            disabled={currentPage === totalPages || totalPages === 0} 
            onClick={() => setCurrentPage(p => p + 1)}
            className="px-3 py-1.5 border border-slate-300 rounded bg-white text-slate-700 hover:bg-slate-100 disabled:opacity-50 disabled:bg-slate-50 shadow-sm transition-colors"
          >
            Sau
          </button>
        </div>
      </div>
    </div>
  );
};

// Chon hoa don de lam viec (dung chung cho man hinh Kiem tra va Dinh khoan). Chon xong dat ?id=... tren URL.
// Cac the loc: "Tat ca" dung dau, roi 3 trang thai chinh (hoa don bi tu choi chi hien o "Tat ca").
const TABS = [
  ["all", "Tất cả", null],
  ["cho_xac_nhan", "Chờ xác nhận", "cho_xac_nhan"],
  ["da_luu", "Đã lưu", "da_luu"],
  ["cho_duyet", "Chờ duyệt", "cho_duyet"],
  ["da_duyet", "Đã duyệt", "da_duyet"],
  ["tu_choi", "Từ chối", "tu_choi"],
];

export default function InvoicePicker({ title, hint }) {
  const [params, setParams] = useSearchParams();
  const user = useUser();
  const [rows, setRows] = useState(null);
  const [tab, setTab] = useState(TABS.some((t) => t[0] === params.get("tab")) ? params.get("tab") : "all");
  const [sending, setSending] = useState(false);
  const [excl, setExcl] = useState(() => new Set());   // hoa don "Da luu" bi bo tick (khong gui)
  const [err, setErr] = useState("");

  // QoL: State quản lý Phân trang
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const load = () => api("/api/invoices?limit=200").then((r) => setRows(r.data)).catch((e) => setErr(e.message));
  useEffect(() => {
    // Sửa lại limit=200 để không bị lỗi 422 từ backend
    api("/api/invoices?limit=200").then((r) => setRows(r.data)).catch((e) => setErr(e.message));
  }, []);

  // Reset về trang 1 mỗi khi đổi tab
  useEffect(() => {
    setCurrentPage(1);
  }, [tab]);

  const open = (id) => setParams({ id: String(id) });
  const count = (st) => (rows || []).filter((r) => !st || r.status === st).length;
  const byId = (a, b) => a.invoice_id - b.invoice_id;
  const newLot = (rows || []).filter((r) => r.status === "cho_xac_nhan").sort(byId);   // lo moi tai len
  const rejLot = (rows || []).filter((r) => r.status === "tu_choi").sort(byId);        // lo bi tu choi
  const savedRows = (rows || []).filter((r) => r.status === "da_luu");
  // Chon de gui: mac dinh chon het, bo tick tung cai khong gui; o dau cot chon/bo chon tat ca
  const picked = savedRows.filter((r) => !excl.has(r.invoice_id));
  const allPicked = savedRows.length > 0 && picked.length === savedRows.length;
  const toggle = (id) => setExcl((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const toggleAll = () => setExcl(allPicked ? new Set(savedRows.map((r) => r.invoice_id)) : new Set());
  async function sendPicked() {
    if (!window.confirm(`Gửi ${picked.length} hóa đơn đã chọn cho kế toán trưởng duyệt?`)) return;
    setSending(true); setErr("");
    try {
      await api("/api/invoices/submit-batch", { method: "POST", body: { invoice_ids: picked.map((r) => r.invoice_id) } });
      setExcl(new Set()); await load(); setTab("cho_duyet");
    } catch (e) { setErr(e.message); }
    setSending(false);
  }
  const cur = TABS.find((t) => t[0] === tab);
  const shown = (rows || []).filter((r) => !cur[2] || r.status === cur[2]);

  // Dữ liệu hiển thị trên trang hiện tại
  const currentRows = shown.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <section className="mx-auto max-w-6xl">
      <h2 className="mb-2 text-2xl font-bold text-slate-800">{title}</h2>
      <p className="mb-4 text-sm text-slate-600">{hint}</p>

      <div className="mb-5 flex flex-wrap items-center gap-3 text-sm" role="tablist">
        {TABS.map(([k, label, st]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`rounded-full px-5 py-2 transition-colors ${tab === k ? "bg-blue-600 font-semibold text-white shadow-sm" : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"}`}>
            {label}{rows ? ` (${count(st)})` : ""}
          </button>
        ))}
      </div>

      {isKTV(user) && (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm">
          <button disabled={newLot.length === 0} onClick={() => open(newLot[0].invoice_id)}
            className="rounded-lg bg-blue-600 px-4 py-1.5 font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-40">Kiểm tra lô mới ({newLot.length})</button>
          <button disabled={rejLot.length === 0} onClick={() => open(rejLot[0].invoice_id)}
            className="rounded-lg bg-red-600 px-4 py-1.5 font-medium text-white shadow-sm hover:bg-red-700 disabled:opacity-40">Kiểm tra lô từ chối ({rejLot.length})</button>
          <span className="text-slate-600">Đã lưu chờ gửi: <b>{savedRows.length}</b> (xem ở tab “Đã lưu”, tick chọn rồi gửi)</span>
          <button disabled={picked.length === 0 || sending} onClick={sendPicked}
            className="ml-auto rounded-lg bg-green-600 px-4 py-1.5 font-semibold text-white shadow-sm hover:bg-green-700 disabled:opacity-40">
            {sending ? "Đang gửi…" : `Gửi ${picked.length} hóa đơn đã chọn`}
          </button>
        </div>
      )}

      {err && <p className="mb-3 text-sm text-red-600">{err}</p>}
      
      <div className="flex flex-col rounded-lg border border-slate-200 bg-white shadow">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase text-slate-600">
              <tr>
                {tab === "da_luu" && isKTV(user) && (
                  <th className="px-4 py-3"><input type="checkbox" aria-label="Chọn tất cả" checked={allPicked} onChange={toggleAll} /></th>)}
                {["#", "Số HĐ", "Ngày", "Người bán", "Tổng tiền", "Trạng thái", ""].map((h) => (
                  <th key={h} className="px-6 py-3 font-semibold">{h}</th>))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {currentRows.map((r) => (
                <tr key={r.invoice_id} className="cursor-pointer transition-colors hover:bg-blue-50" onClick={() => open(r.invoice_id)}>
                  {tab === "da_luu" && isKTV(user) && (
                    <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" aria-label={`Chọn hóa đơn ${r.invoice_id}`} checked={!excl.has(r.invoice_id)} onChange={() => toggle(r.invoice_id)} />
                    </td>)}
                  <td className="px-6 py-4 text-slate-500">{r.invoice_id}</td>
                  <td className="px-6 py-4 font-medium">{r.invoice_number || "—"}</td>
                  <td className="px-6 py-4">{dateVN(r.invoice_date)}</td>
                  {/* Ép IN HOA (uppercase) tên người bán để chống lỗi font Unicode */}
                  <td className="max-w-[24rem] truncate px-6 py-4 font-medium uppercase tracking-wide text-slate-700" title={r.seller_name}>{r.seller_name || "—"}</td>
                  <td className="px-6 py-4 text-right font-medium tabular-nums text-slate-800">{money(r.total_amount)}</td>
                  <td className="px-6 py-4"><StatusBadge status={r.status} /></td>
                  <td className="px-6 py-4 text-right">
                    <button onClick={(e) => { e.stopPropagation(); open(r.invoice_id); }}
                      className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white shadow hover:bg-blue-700 transition-colors">Mở</button>
                  </td>
                </tr>
              ))}
              {rows && shown.length === 0 && (
                <tr><td colSpan={8} className="px-6 py-12 text-center text-sm text-slate-500">
                  {tab === "all" ? "Chưa có hóa đơn nào." : `Không có hóa đơn nào ở mục “${cur[1]}”.`}
                </td></tr>
              )}
              {!rows && !err && <tr><td colSpan={7} className="px-6 py-12 text-center text-sm text-slate-500">Đang tải…</td></tr>}
            </tbody>
          </table>
        </div>
        
        {/* Thanh Phân trang */}
        {shown.length > 0 && (
          <Pagination 
            totalItems={shown.length}
            pageSize={pageSize}
            currentPage={currentPage}
            setPageSize={setPageSize}
            setCurrentPage={setCurrentPage}
          />
        )}
      </div>
    </section>
  );
}