import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client.js";
import InvoiceDetail from "./InvoiceDetail.jsx";
import StatusBadge from "./StatusBadge.jsx";
import { dateVN, FILE_TYPE, money, STATUS } from "./format.js";
import Pagination from "../../components/Pagination.jsx";

// Danh sach hoa don + bo loc.
export default function InvoiceList({ refreshKey = 0 }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState("");

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10); 

  // State cho Pop-up Xóa và Mật khẩu
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [password, setPassword] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteErr, setDeleteErr] = useState("");

  const load = useCallback(() => {
    const p = new URLSearchParams({ 
      limit: pageSize.toString(),
      offset: ((currentPage - 1) * pageSize).toString() 
    });
    
    if (q.trim()) p.set("q", q.trim());
    if (status) p.set("status", status);
    
    return api(`/api/invoices?${p}`).then((r) => { 
      setRows(r.data); 
      setTotal(r.total || r.data.length);
      setErr(""); 
    }).catch((e) => setErr(e.message));
  }, [q, status, currentPage, pageSize]); 

  useEffect(() => {
    setCurrentPage(1);
  }, [q, status]);

  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load, refreshKey]);

  const processing = rows.some((r) => r.status === "dang_xu_ly");
  useEffect(() => {
    if (!processing) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [processing, load]);

  const requestDelete = (id) => {
    setDeleteConfirmId(id);
    setPassword("");
    setDeleteErr("");
  };

  const handleExecuteDelete = async (e) => {
    e.preventDefault();
    if (!password.trim()) {
      setDeleteErr("Vui lòng nhập mật khẩu xác nhận!");
      return;
    }

    setIsDeleting(true);
    setDeleteErr("");

    try {
      // Gọi API xóa (có thể truyền kèm mật khẩu trong body hoặc header tùy backend của bạn, ở đây gửi body json)
      await api(`/api/invoices/${deleteConfirmId}`, { 
        method: "DELETE",
        body: { password: password.trim() } 
      });
      load();
      setDeleteConfirmId(null);
      setPassword("");
    } catch (error) {
      setDeleteErr(error.message || "Mật khẩu không đúng hoặc lỗi xóa hóa đơn.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <section className="relative">
      {/* POP-UP XÁC NHẬN XÓA BẰNG MẬT KHẨU */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm transition-opacity">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
            <form onSubmit={handleExecuteDelete} className="p-6 text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 border-4 border-red-50 shadow-inner">
                <span className="text-3xl font-bold text-red-600">🔒</span>
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Xác thực mật khẩu</h3>
              <p className="text-slate-600 mb-4 leading-relaxed text-sm">
                Bạn đang yêu cầu xóa vĩnh viễn Hóa đơn <b className="text-slate-900">#{deleteConfirmId}</b>. Vui lòng nhập mật khẩu tài khoản để tiếp tục.
              </p>
              
              <div className="mb-4 text-left">
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Mật khẩu xác nhận</label>
                <input 
                  type="password" 
                  placeholder="Nhập mật khẩu của bạn..." 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-red-500 shadow-sm"
                  autoFocus
                  required
                />
                {deleteErr && <p className="mt-1 text-xs text-red-600 font-medium">{deleteErr}</p>}
              </div>

              <div className="flex gap-3 justify-center">
                <button 
                  type="button"
                  disabled={isDeleting}
                  onClick={() => setDeleteConfirmId(null)} 
                  className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-bold transition-colors w-1/2">
                  Hủy bỏ
                </button>

                <button 
                  type="submit"
                  disabled={isDeleting}
                  className="px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold transition-colors shadow-md w-1/2 flex items-center justify-center"
                >
                  {isDeleting ? "Đang xử lý..." : "Xác nhận Xóa"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm số HĐ, người bán, MST, tên file"
          className="w-72 rounded border p-2 text-sm focus:outline-none focus:border-blue-500" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded border p-2 text-sm focus:outline-none focus:border-blue-500">
          <option value="">Mọi trạng thái</option>
          {Object.entries(STATUS).map(([k, [label]]) => <option key={k} value={k}>{label}</option>)}
        </select>
      </div>
      {err && <p className="mb-2 text-sm text-red-600">{err}</p>}
      
      <div className="overflow-x-auto rounded border bg-white flex flex-col shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase text-slate-600">
            <tr>{["Tệp", "Loại", "Số HĐ", "Ngày", "Người bán", "MST", "Tổng tiền", "Trạng thái", "Thao tác"].map((h) => (
              <th key={h} className="px-3 py-3 font-semibold">{h}</th>))}</tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r) => (
              <tr key={r.invoice_id} className="hover:bg-slate-50 transition-colors">
                <td className="max-w-[12rem] truncate px-3 py-3 text-slate-700" title={r.filename}>{r.filename}</td>
                <td className="px-3 py-3 font-medium text-slate-600">{FILE_TYPE[r.file_type]}</td>
                <td className="px-3 py-3 font-medium text-blue-700">{r.invoice_number || "—"}</td>
                <td className="px-3 py-3 text-slate-600">{dateVN(r.invoice_date)}</td>
                <td className="max-w-[14rem] truncate px-3 py-3 font-medium text-slate-800 uppercase tracking-wide" title={r.seller_name}>{r.seller_name ? r.seller_name.normalize("NFC") : "—"}</td>
                <td className="px-3 py-3 text-slate-600">{r.mst_seller || "—"}</td>
                <td className="px-3 py-3 text-right font-medium tabular-nums text-slate-800">{money(r.total_amount)}</td>
                <td className="px-3 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-3 py-3">
                  <div className="flex items-center gap-3">
                    <button className="text-blue-600 hover:text-blue-800 font-medium transition-colors" onClick={() => setSelected(r.invoice_id)}>
                      Xem
                    </button>
                    <button className="text-red-500 hover:text-red-700 font-medium transition-colors" onClick={() => requestDelete(r.invoice_id)}>
                      Xóa
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={9} className="px-3 py-12 text-center text-slate-500">Chưa có hóa đơn nào.</td></tr>
            )}
          </tbody>
        </table>
        
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