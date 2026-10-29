import React, { useState, useEffect } from "react";
import { api } from "../../api/client.js";
import Pagination from "../../components/Pagination.jsx";
import FileViewer from "../review/FileViewer.jsx";

// Cửa sổ đối chiếu nhanh dành cho Kế toán trưởng
const QuickReviewModal = ({ invoiceId, onClose, onApprove, onReject }) => {
  const [inv, setInv] = useState(null);
  const [entries, setEntries] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let dead = false;
    setLoading(true);

    // File goc do FileViewer tu tai (anh / PDF / XML dang hoa don), o day chi lay du lieu va but toan
    Promise.all([
      api(`/api/invoices/${invoiceId}`),
      api(`/api/invoices/${invoiceId}/journal-entries`).catch(() => ({ data: [] })),
    ]).then(([invRes, entriesRes]) => {
      if (dead) return;
      setInv(invRes.data);
      setEntries(entriesRes.data || []);
      setLoading(false);
    }).catch(err => {
      console.error("Lỗi tải chi tiết:", err);
      if (!dead) setLoading(false);
    });

    return () => { dead = true; };
  }, [invoiceId]);

  if (loading) return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 text-white backdrop-blur-sm">
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        Đang tải dữ liệu đối chiếu...
      </div>
    </div>
  );
  if (!inv) return null;

  const formatMoney = (v) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(v || 0);

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-slate-100 animate-in fade-in zoom-in-95 duration-200">
      <div className="flex justify-between items-center bg-white px-6 py-3 border-b shadow-sm">
         <div className="flex items-center gap-4">
           <h2 className="text-xl font-bold text-slate-800">Đối chiếu nhanh: Hóa đơn #{inv.invoice_id}</h2>
           {inv.is_anomaly && <span className="bg-red-600 text-white px-2 py-0.5 rounded text-xs font-bold shadow-sm">⚠️ Rủi ro cao</span>}
         </div>
         <div className="flex gap-3">
            <button onClick={() => onApprove(inv.invoice_id)} className="bg-green-600 hover:bg-green-700 text-white px-5 py-1.5 rounded font-medium shadow-sm transition-colors">
              ✓ Duyệt nhanh
            </button>
            <button onClick={() => { onClose(); onReject(inv.invoice_id); }} className="bg-red-600 hover:bg-red-700 text-white px-5 py-1.5 rounded font-medium shadow-sm transition-colors">
              ✕ Từ chối
            </button>
            <div className="w-px bg-slate-300 mx-1"></div>
            <button onClick={onClose} className="bg-slate-200 hover:bg-slate-300 text-slate-800 px-4 py-1.5 rounded font-medium transition-colors">
              Đóng
            </button>
         </div>
      </div>
      
      <div className="flex flex-1 overflow-hidden">
         <div className="w-1/2 border-r border-slate-300 bg-slate-200 flex flex-col">
            <FileViewer invoiceId={inv.invoice_id} fileType={inv.file_type} filename={inv.filename} />
         </div>

         <div className="w-1/2 bg-white p-8 overflow-y-auto">
            {inv.is_anomaly && (
              <div className="mb-6 bg-red-50 border border-red-200 p-4 rounded-lg shadow-sm">
                <h3 className="text-red-800 font-bold mb-1 flex items-center gap-2">⚠️ Cảnh báo bất thường (AI Isolation Forest)</h3>
                <p className="text-red-700 text-sm font-medium">{inv.anomaly_reason}</p>
              </div>
            )}

            <h3 className="font-bold text-slate-800 text-lg mb-4 border-b pb-2">Dữ liệu trích xuất</h3>
            <div className="grid grid-cols-2 gap-y-6 gap-x-8 text-sm bg-slate-50 p-6 rounded-xl border border-slate-200 shadow-inner">
               <div>
                 <span className="block text-slate-500 text-xs uppercase font-semibold mb-1">Số hóa đơn</span>
                 <strong className="text-lg text-slate-900">{inv.invoice_number || "—"}</strong>
               </div>
               <div>
                 <span className="block text-slate-500 text-xs uppercase font-semibold mb-1">Ngày lập</span>
                 <strong className="text-lg text-slate-900">{inv.invoice_date || "—"}</strong>
               </div>
               
               <div className="col-span-2">
                 <span className="block text-slate-500 text-xs uppercase font-semibold mb-1">Người bán</span>
                 <strong className="text-xl text-blue-700 uppercase font-bold tracking-wide">{inv.seller_name || "—"}</strong>
               </div>
               <div className="col-span-2">
                 <span className="block text-slate-500 text-xs uppercase font-semibold mb-1">Mã số thuế</span>
                 <strong className="text-lg text-slate-900">{inv.mst_seller || "—"}</strong>
               </div>
               
               <div>
                 <span className="block text-slate-500 text-xs uppercase font-semibold mb-1">Tiền trước thuế</span>
                 <strong className="text-lg text-slate-700">{formatMoney(inv.total_before_tax)}</strong>
               </div>
               <div>
                 <span className="block text-slate-500 text-xs uppercase font-semibold mb-1">Tiền thuế VAT</span>
                 <strong className="text-lg text-slate-700">{formatMoney(inv.vat_amount)}</strong>
               </div>
               
               <div className="col-span-2 mt-2 pt-4 border-t border-slate-300">
                 <span className="block text-slate-500 text-xs uppercase font-semibold mb-1">Tổng thanh toán</span>
                 <strong className="text-3xl text-green-700">{formatMoney(inv.total_amount)}</strong>
               </div>
            </div>

            <div className="mt-8">
              <h3 className="font-bold text-slate-800 text-lg mb-4 border-b pb-2">Chi tiết Định khoản (Bút toán)</h3>
              {entries && entries.length > 0 ? (
                <div className="rounded-lg border border-slate-200 overflow-hidden">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Tài khoản Nợ</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Tài khoản Có</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Số tiền</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 bg-white">
                      {entries.map((e, idx) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-800">{e.debit_account}</td>
                          <td className="px-4 py-3 font-medium text-slate-800">{e.credit_account}</td>
                          <td className="px-4 py-3 text-right font-medium text-blue-700 tabular-nums">{formatMoney(e.amount)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-slate-50 border-t border-slate-200">
                      <tr>
                        <td colSpan="2" className="px-4 py-3 text-right text-sm font-semibold text-slate-600">Tổng cộng:</td>
                        <td className="px-4 py-3 text-right text-sm font-bold text-green-700 tabular-nums">
                          {formatMoney(entries.reduce((sum, e) => sum + (Number(e.amount) || 0), 0))}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              ) : (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm font-medium">
                  ⚠️ Kế toán viên chưa lưu bút toán nào cho hóa đơn này! Vui lòng nhắc nhở bổ sung.
                </div>
              )}
            </div>
         </div>
      </div>
    </div>
  );
};

export default function Approvals() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const [rejectingId, setRejectingId] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  
  const [confirmApproveId, setConfirmApproveId] = useState(null);
  const [showAnomalyModal, setShowAnomalyModal] = useState(false);
  const [viewingId, setViewingId] = useState(null);
  const [highlightedId, setHighlightedId] = useState(null);

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const fetchApprovals = () => {
    setLoading(true);
    api("/api/approvals")
      .then((res) => {
        setInvoices(res?.data || res || []);
        setCurrentPage(1);
      })
      .catch((err) => console.error("Lỗi tải data:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchApprovals(); }, []);
  useEffect(() => { setCurrentPage(1); }, [searchQuery]);

  const removeAccents = (str) => {
    return str ? str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase() : "";
  };

  const filteredInvoices = invoices.filter(inv => {
    if (!searchQuery.trim()) return true;
    const query = removeAccents(searchQuery);
    const seller = removeAccents(inv.seller_name || inv.vendor);
    const invNum = inv.invoice_number ? String(inv.invoice_number).toLowerCase() : "";
    const invId = String(inv.invoice_id || inv.id);
    return seller.includes(query) || invNum.includes(query) || invId.includes(query);
  });

  const handleConfirmApprove = (id) => setConfirmApproveId(id);

  const executeApprove = () => {
    if (!confirmApproveId) return;
    setSubmitting(true);
    api(`/api/invoices/${confirmApproveId}/approve`, { method: "POST" })
      .then(() => {
        alert(`Hóa đơn ${confirmApproveId} đã được phê duyệt!`);
        if (rejectingId === confirmApproveId) closeRejectForm(); 
        if (viewingId === confirmApproveId) setViewingId(null);
        setConfirmApproveId(null);
        fetchApprovals();
      })
      .catch(() => alert("Lỗi khi duyệt hóa đơn."))
      .finally(() => setSubmitting(false));
  };

  const openRejectForm = (id) => { setRejectingId(id); setRejectReason(""); };
  const closeRejectForm = () => { setRejectingId(null); setRejectReason(""); };

  const submitReject = (e) => {
    e.preventDefault();
    if (!rejectReason.trim()) { alert("Vui lòng nhập lý do từ chối!"); return; }
    setSubmitting(true);
    api(`/api/invoices/${rejectingId}/reject?reason=${encodeURIComponent(rejectReason)}`, { method: "POST" })
      .then(() => {
        alert(`Hóa đơn ${rejectingId} đã bị từ chối.`);
        closeRejectForm();
        if (viewingId === rejectingId) setViewingId(null);
        fetchApprovals();
      })
      .catch(() => alert("Lỗi khi từ chối hóa đơn."))
      .finally(() => setSubmitting(false));
  };

  const scrollToInvoice = (id) => {
    setShowAnomalyModal(false);
    const index = filteredInvoices.findIndex(inv => (inv.invoice_id || inv.id) === id);
    if (index !== -1) {
      const targetPage = Math.floor(index / pageSize) + 1;
      if (currentPage !== targetPage) setCurrentPage(targetPage);
      setTimeout(() => {
        const rowElement = document.getElementById(`invoice-row-${id}`);
        if (rowElement) {
          rowElement.scrollIntoView({ behavior: "smooth", block: "center" });
          setHighlightedId(id);
          setTimeout(() => setHighlightedId(null), 3000);
        }
      }, 150);
    }
  };

  const currentInvoices = filteredInvoices.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  if (loading) return <div className="p-8 text-center text-slate-500">Đang tải dữ liệu...</div>;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200 relative">
      {confirmApproveId && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm transition-opacity">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4 border-4 border-green-50 shadow-inner">
                <span className="text-3xl font-bold text-green-600">✓</span>
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Xác nhận phê duyệt</h3>
              <p className="text-slate-600 mb-8 leading-relaxed text-sm">
                Bạn có chắc chắn muốn duyệt Hóa đơn <b className="text-slate-900">#{confirmApproveId}</b> không? Dữ liệu sẽ chính thức được ghi nhận.
              </p>
              <div className="flex gap-3 justify-center">
                <button disabled={submitting} onClick={() => setConfirmApproveId(null)} className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-bold transition-colors w-1/2">Hủy bỏ</button>
                <button disabled={submitting} onClick={executeApprove} className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold transition-colors shadow-md w-1/2 flex justify-center items-center">{submitting ? "Đang xử lý..." : "Đồng ý Duyệt"}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {viewingId && <QuickReviewModal invoiceId={viewingId} onClose={() => setViewingId(null)} onApprove={handleConfirmApprove} onReject={openRejectForm} />}

      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-bold text-slate-800">Hàng chờ duyệt</h2>
          <button onClick={() => setShowAnomalyModal(true)} className="flex items-center gap-2 bg-orange-100 hover:bg-orange-200 text-orange-800 border border-orange-200 px-3 py-1.5 rounded text-sm font-semibold transition-colors shadow-sm">
            Cảnh báo rủi ro ({invoices.filter(i => i.is_anomaly).length})
          </button>
        </div>
        
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="relative w-full md:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><span className="text-slate-400">🔍</span></div>
            <input type="text" placeholder="Tìm Nhà cung cấp, Số HĐ..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full pl-10 pr-8 py-1.5 border border-slate-300 rounded text-sm focus:outline-none focus:border-blue-500" />
            {searchQuery && <button onClick={() => setSearchQuery("")} className="absolute inset-y-0 right-0 pr-2 flex items-center text-slate-400 hover:text-slate-600 font-bold">✕</button>}
          </div>
          {rejectingId && <button onClick={closeRejectForm} className="text-sm font-medium text-slate-500 hover:text-slate-700 bg-white border border-slate-300 px-3 py-1.5 rounded transition-colors whitespace-nowrap">Đóng form</button>}
        </div>
      </div>

      {showAnomalyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl overflow-hidden border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
              <h3 className="text-lg font-bold text-red-700">Danh sách Hóa đơn có rủi ro cao</h3>
              <button onClick={() => setShowAnomalyModal(false)} className="text-slate-400 hover:text-slate-700 text-xl font-bold">✕</button>
            </div>
            <div className="p-6 max-h-[60vh] overflow-y-auto bg-slate-50/50">
              {invoices.filter(i => i.is_anomaly).length === 0 ? (
                <div className="text-center text-slate-500 py-8">Không có hóa đơn nào bất thường.</div>
              ) : (
                <ul className="space-y-4">
                  {invoices.filter(i => i.is_anomaly).map(inv => (
                    <li key={inv.invoice_id || inv.id} className="p-4 border border-red-200 bg-red-50 rounded-md shadow-sm">
                      <div className="flex justify-between items-start mb-2">
                        <div className="font-bold text-slate-800 text-base">Hóa đơn #{inv.invoice_number || inv.invoice_id || inv.id}</div>
                        <div className="flex items-center gap-3">
                          <div className="font-bold text-red-600">{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(inv.total_amount || inv.total || 0)}</div>
                          <button onClick={() => scrollToInvoice(inv.invoice_id || inv.id)} className="bg-blue-100 hover:bg-blue-200 text-blue-700 px-3 py-1 rounded text-xs font-bold transition-colors shadow-sm">Đi tới ➔</button>
                        </div>
                      </div>
                      <div className="text-sm text-slate-700 mb-1"><span className="font-semibold">Nhà cung cấp:</span> {inv.seller_name || inv.vendor || "N/A"}</div>
                      <div className="text-sm text-red-700 bg-white inline-block px-2 py-1 rounded border border-red-100 font-medium">{inv.anomaly_reason}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {rejectingId && (
        <form onSubmit={submitReject} className="p-6 bg-red-50 border-b border-red-200 flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 w-full">
            <label className="block text-xs font-semibold text-red-800 uppercase mb-1">Lý do từ chối Hóa đơn #{rejectingId} <span className="text-red-600">*</span></label>
            <input type="text" placeholder="VD: Sai mã số thuế, số tiền không khớp PO..." value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} className="w-full border border-red-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-red-500 bg-white" autoFocus required />
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={closeRejectForm} className="bg-slate-300 hover:bg-slate-400 text-slate-800 px-4 py-2 rounded text-sm font-medium transition-colors">Hủy</button>
            <button type="submit" disabled={submitting} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors">{submitting ? "Đang xử lý..." : "Xác nhận từ chối"}</button>
          </div>
        </form>
      )}

      {filteredInvoices.length === 0 ? (
        <div className="p-12 text-center text-slate-500">{searchQuery ? `Không tìm thấy hóa đơn nào chứa "${searchQuery}".` : "Không có hóa đơn nào đang chờ duyệt."}</div>
      ) : (
        <div className="flex flex-col">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-100">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Số hóa đơn</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Nhà cung cấp</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Tổng tiền</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {currentInvoices.map((inv) => {
                  const currentId = inv.invoice_id || inv.id;
                  const isRejecting = rejectingId === currentId;
                  const isHighlighted = highlightedId === currentId;
                  return (
                    <tr id={`invoice-row-${currentId}`} key={currentId} className={`${isHighlighted ? "bg-blue-50 ring-2 ring-blue-400 ring-inset shadow-inner" : isRejecting ? "bg-red-100" : inv.is_anomaly ? "bg-red-50 hover:bg-red-100" : "hover:bg-slate-50"} transition-colors`}>
                      <td className={`px-6 py-4 text-sm ${inv.is_anomaly ? "text-red-700 font-bold" : "text-slate-900"}`}>{currentId}</td>
                      <td className={`px-6 py-4 text-sm font-medium ${inv.is_anomaly ? "text-red-600" : "text-blue-600"}`}>{inv.invoice_number || "N/A"}</td>
                      <td className="px-6 py-4 text-sm text-slate-500">
                        <div className={`font-medium uppercase tracking-wide ${inv.is_anomaly ? "text-red-700" : "text-slate-700"}`}>
                          {inv.seller_name || inv.vendor || "N/A"}
                          {inv.is_anomaly && <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-red-600 text-white">⚠️ Bất thường</span>}
                        </div>
                      </td>
                      <td className={`px-6 py-4 text-sm font-semibold ${inv.is_anomaly ? "text-red-700" : "text-slate-900"}`}>{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(inv.total_amount || inv.total || 0)}</td>
                      <td className="px-6 py-4 text-center text-sm font-medium whitespace-nowrap">
                        <button onClick={() => setViewingId(currentId)} className="text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 px-3 py-1.5 rounded mr-2 shadow-sm">👁️ Kiểm tra</button>
                        <button onClick={() => handleConfirmApprove(currentId)} className="text-white bg-green-600 hover:bg-green-700 px-3 py-1.5 rounded mr-2 shadow-sm">Duyệt</button>
                        <button onClick={() => openRejectForm(currentId)} className={`px-3 py-1.5 rounded shadow-sm ${isRejecting ? "bg-red-800 text-white" : "text-white bg-red-600 hover:bg-red-700"}`}>Từ chối</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Pagination totalItems={filteredInvoices.length} pageSize={pageSize} currentPage={currentPage} setPageSize={setPageSize} setCurrentPage={setCurrentPage} />
        </div>
      )}
    </div>
  );
}