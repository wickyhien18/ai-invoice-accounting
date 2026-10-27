import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client.js";
import InvoiceDetail from "./InvoiceDetail.jsx";
import StatusBadge from "./StatusBadge.jsx";
import { dateVN, FILE_TYPE, money, STATUS } from "./format.js";

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
          <option value={100}>100</option>
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


// Danh sach hoa don + bo loc. `refreshKey` doi gia tri thi tai lai (trang tai len dung de bao co hoa don moi).
export default function InvoiceList({ refreshKey = 0 }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState("");

  // THÊM MỚI: State phân trang
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10); // Mặc định hiển thị 10 dòng

  const load = useCallback(() => {
    // SỬA: Đưa tham số phân trang vào API
    const p = new URLSearchParams({ 
      limit: pageSize.toString(),
      offset: ((currentPage - 1) * pageSize).toString() // Nếu backend dùng page thay vì offset, đổi thành page: currentPage
    });
    
    if (q.trim()) p.set("q", q.trim());
    if (status) p.set("status", status);
    
    return api(`/api/invoices?${p}`).then((r) => { 
      setRows(r.data); 
      setTotal(r.total || r.data.length); // Fallback nếu backend không trả về total
      setErr(""); 
    }).catch((e) => setErr(e.message));
  }, [q, status, currentPage, pageSize]); // Theo dõi thêm currentPage và pageSize

  // Reset về trang 1 khi gõ tìm kiếm hoặc đổi filter
  useEffect(() => {
    setCurrentPage(1);
  }, [q, status]);

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
      </div>
      {err && <p className="mb-2 text-sm text-red-600">{err}</p>}
      
      <div className="overflow-x-auto rounded border bg-white flex flex-col">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase text-slate-600">
            <tr>{["Tệp", "Loại", "Số HĐ", "Ngày", "Người bán", "MST", "Tổng tiền", "Trạng thái", ""].map((h) => (
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
                <td className="px-3 py-2"><button className="text-blue-700" onClick={() => setSelected(r.invoice_id)}>Xem</button></td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={9} className="px-3 py-8 text-center text-slate-500">Chưa có hóa đơn nào.</td></tr>
            )}
          </tbody>
        </table>
        
        {/* TÍCH HỢP PHÂN TRANG VÀO ĐÂY */}
        {total > 0 && (
          <Pagination 
            totalItems={total}
            pageSize={pageSize}
            currentPage={currentPage}
            setPageSize={setPageSize}
            setCurrentPage={setCurrentPage}
          />
        )}
      </div>
      
      {selected && <InvoiceDetail invoiceId={selected} onClose={() => setSelected(null)} onChanged={load} />}
    </section>
  );
}