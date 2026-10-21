import React, { useState, useEffect } from "react";
import Placeholder from "../components/Placeholder.jsx";
import { api } from "../api/client.js";
import UploadPage from "./invoices/Upload.jsx";

export const Upload = UploadPage;
export const Review = () => <Placeholder title="Kiểm tra trường trích xuất" pkg="B" tasks="B3 (ảnh trái, trường phải, màu độ tin cậy)" />;
export const Entries = () => <Placeholder title="Bút toán gợi ý" pkg="B" tasks="B6, B7 (gợi ý Nợ/Có, lưu bút toán)" />;

// ---------------------------------------------------------
// Nhiệm vụ C3: Luồng duyệt & Hàng chờ duyệt
// ---------------------------------------------------------
export const Approvals = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  // State cho Form Từ chối
  const [rejectingId, setRejectingId] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchApprovals = () => {
    setLoading(true);
    api("/api/approvals")
      .then((res) => setInvoices(res?.data || res || []))
      .catch((err) => console.error("Lỗi tải data:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleApprove = (id) => {
    api(`/api/invoices/${id}/approve`, { method: "POST" })
      .then(() => {
        alert(`Hóa đơn ${id} đã được phê duyệt!`);
        // Đóng form từ chối nếu đang mở trùng ID
        if (rejectingId === id) closeRejectForm(); 
        fetchApprovals();
      })
      .catch(() => alert("Lỗi khi duyệt hóa đơn. Bạn có đúng quyền Kế Toán Trưởng không?"));
  };

  // Mở/Đóng form từ chối
  const openRejectForm = (id) => {
    setRejectingId(id);
    setRejectReason("");
  };

  const closeRejectForm = () => {
    setRejectingId(null);
    setRejectReason("");
  };

  // Gửi API từ chối
  const submitReject = (e) => {
    e.preventDefault();
    if (!rejectReason.trim()) {
      alert("Vui lòng nhập lý do từ chối!");
      return;
    }
    
    setSubmitting(true);
    api(`/api/invoices/${rejectingId}/reject?reason=${encodeURIComponent(rejectReason)}`, { method: "POST" })
      .then(() => {
        alert(`Hóa đơn ${rejectingId} đã bị từ chối.`);
        closeRejectForm();
        fetchApprovals();
      })
      .catch(() => alert("Lỗi khi từ chối hóa đơn."))
      .finally(() => setSubmitting(false));
  };

  if (loading) return <div className="p-8 text-center text-slate-500">Đang tải dữ liệu...</div>;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200">
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
        <h2 className="text-lg font-bold text-slate-800">Hàng chờ duyệt</h2>
        {rejectingId && (
          <button 
            onClick={closeRejectForm}
            className="text-sm font-medium text-slate-500 hover:text-slate-700 bg-white border border-slate-300 px-3 py-1.5 rounded transition-colors"
          >
            Đóng form
          </button>
        )}
      </div>

      {/* Form Nhập Lý Do Từ Chối (Giống thiết kế nhập PO) */}
      {rejectingId && (
        <form onSubmit={submitReject} className="p-6 bg-red-50 border-b border-red-200 flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 w-full">
            <label className="block text-xs font-semibold text-red-800 uppercase mb-1">
              Lý do từ chối Hóa đơn #{rejectingId} <span className="text-red-600">*</span>
            </label>
            <input 
              type="text" 
              placeholder="VD: Sai mã số thuế, số tiền không khớp PO..." 
              value={rejectReason} 
              onChange={(e) => setRejectReason(e.target.value)}
              className="w-full border border-red-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-red-500 bg-white"
              autoFocus
              required
            />
          </div>
          <div className="flex gap-2">
            <button 
              type="button" 
              onClick={closeRejectForm}
              className="bg-slate-300 hover:bg-slate-400 text-slate-800 px-4 py-2 rounded text-sm font-medium transition-colors shadow-sm"
            >
              Hủy
            </button>
            <button 
              type="submit" 
              disabled={submitting}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
            >
              {submitting ? "Đang xử lý..." : "Xác nhận từ chối"}
            </button>
          </div>
        </form>
      )}

      {invoices.length === 0 ? (
        <div className="p-8 text-center text-slate-500">Không có hóa đơn nào đang chờ duyệt.</div>
      ) : (
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
            {invoices.map((inv) => {
              const currentId = inv.invoice_id || inv.id;
              const isRejecting = rejectingId === currentId;

              return (
                <tr key={currentId} className={isRejecting ? "bg-red-50 transition-colors" : "hover:bg-slate-50 transition-colors"}>
                  <td className="px-6 py-4 text-sm text-slate-900">{currentId}</td>
                  <td className="px-6 py-4 text-sm font-medium text-blue-600">{inv.invoice_number || "N/A"}</td>
                  <td className="px-6 py-4 text-sm text-slate-500">
                    <div className="font-medium text-slate-700">{inv.seller_name || inv.vendor || "N/A"}</div>
                    {/* Đoạn code thêm mới cho Nhiệm vụ C5 */}
                    {inv.is_anomaly && (
                      <div className="mt-1 text-xs font-bold text-red-600 bg-red-50 p-1.5 rounded inline-block border border-red-200 shadow-sm">
                        ⚠️ {inv.anomaly_reason}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm font-semibold text-slate-900">
                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(inv.total_amount || inv.total || 0)}
                  </td>
                  <td className="px-6 py-4 text-center text-sm font-medium">
                    <button 
                      onClick={() => handleApprove(currentId)} 
                      className="text-white bg-green-600 hover:bg-green-700 px-3 py-1.5 rounded mr-2 shadow-sm transition-all"
                    >
                      Duyệt
                    </button>
                    <button 
                      onClick={() => openRejectForm(currentId)} 
                      className={`px-3 py-1.5 rounded shadow-sm transition-all ${isRejecting ? "bg-red-800 text-white" : "text-white bg-red-600 hover:bg-red-700"}`}
                    >
                      Từ chối
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
};

// ---------------------------------------------------------
// Nhiệm vụ C6: Nhập và Quản lý PO
// ---------------------------------------------------------
export const PurchaseOrders = () => {
  const [pos, setPos] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [showForm, setShowForm] = useState(false);
  const [poNumber, setPoNumber] = useState("");
  const [vendor, setVendor] = useState("");
  const [amount, setAmount] = useState("");

  const fetchPOs = () => {
    setLoading(true);
    api("/api/purchase-orders")
      .then((res) => setPos(res?.data || res || []))
      .catch((err) => console.error("Lỗi tải data PO:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPOs();
  }, []);

  const handleCreatePO = (e) => {
    e.preventDefault();
    if (!poNumber || !vendor || !amount) {
      alert("Vui lòng điền đầy đủ thông tin PO!");
      return;
    }

    const payload = {
      po_number: poNumber.trim(),
      vendor: vendor.trim(),
      order_date: new Date().toISOString().split('T')[0],
      expected_amount: parseFloat(amount)
    };

    api("/api/purchase-orders", { method: "POST", body: payload })
      .then(() => {
        alert("Đã tạo Đơn mua hàng (PO) mới thành công!");
        setPoNumber("");
        setVendor("");
        setAmount("");
        setShowForm(false);
        fetchPOs(); 
      })
      .catch((err) => alert("Lỗi: " + (err.message || "Không thể tạo PO")));
  };

  if (loading) return <div className="p-8 text-center text-slate-500">Đang tải dữ liệu Đơn mua hàng...</div>;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200">
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
        <h2 className="text-lg font-bold text-slate-800">Danh sách Đơn mua hàng (PO)</h2>
        <button 
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
        >
          {showForm ? "Đóng form" : "+ Thêm PO mới"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreatePO} className="p-6 bg-slate-50 border-b border-slate-200 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Mã PO</label>
            <input 
              type="text" 
              placeholder="VD: PO-2026-067" 
              value={poNumber} 
              onChange={(e) => setPoNumber(e.target.value)}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Nhà cung cấp</label>
            <input 
              type="text" 
              placeholder="VD: Công ty TNHH Bờ Đen" 
              value={vendor} 
              onChange={(e) => setVendor(e.target.value)}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Tổng tiền dự kiến (VNĐ)</label>
            <input 
              type="number" 
              placeholder="VD: 15000000" 
              value={amount} 
              onChange={(e) => setAmount(e.target.value)}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <button 
              type="submit" 
              className="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors shadow-sm"
            >
              Lưu PO
            </button>
          </div>
        </form>
      )}
      
      {pos.length === 0 ? (
        <div className="p-8 text-center text-slate-500">Chưa có Đơn mua hàng nào trong hệ thống.</div>
      ) : (
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Mã PO</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Nhà cung cấp</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Ngày đặt</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Tổng tiền dự kiến</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Trạng thái</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {pos.map((po) => (
              <tr key={po.po_id || po.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-6 py-4 text-sm text-slate-900">{po.po_id || po.id}</td>
                <td className="px-6 py-4 text-sm font-medium text-blue-600">{po.po_number}</td>
                <td className="px-6 py-4 text-sm text-slate-500">{po.vendor}</td>
                <td className="px-6 py-4 text-sm text-slate-500">{po.order_date}</td>
                <td className="px-6 py-4 text-sm font-semibold text-slate-900">
                  {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(po.expected_amount || 0)}
                </td>
                <td className="px-6 py-4 text-center text-sm">
                  <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs font-medium">
                    {po.status === 'dang_mo' ? 'Đang mở' : po.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

// ---------------------------------------------------------
// Nhiệm vụ C4: Xuất bảng kê
// ---------------------------------------------------------
export const Export = () => {
  const [loading, setLoading] = useState(false);

  const handleExport = () => {
    setLoading(true);
    api("/api/exports/sheet", { method: "POST" })
      .then((res) => {
        alert(res.message);
        // Tự động kích hoạt tải file về máy tính
        if (res.download_url) {
          const a = document.createElement("a");
          a.href = res.download_url; // Vite proxy sẽ tự nối thành localhost:8000/api/...
          a.download = "";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }
      })
      .catch((err) => {
        alert("Lỗi xuất file: " + (err.message || "Hãy đảm bảo có ít nhất 1 hóa đơn đang ở Hàng chờ được KTT bấm Duyệt."));
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200 p-8 max-w-2xl mx-auto mt-6 text-center">
      <h2 className="text-2xl font-bold text-slate-800 mb-4">Xuất bảng kê 01-2/GTGT</h2>
      <p className="text-slate-600 mb-8 leading-relaxed">
        Tính năng này sẽ rà soát hệ thống để gom tất cả các hóa đơn <b>Đã duyệt</b> và <b>Chưa xuất</b> thành một file Excel chuẩn theo mẫu 01-2/GTGT của Bộ Tài chính.<br/> 
        Sau khi xuất thành công, các hóa đơn này sẽ được tự động cập nhật trạng thái thành <b>Đã xuất</b> để tránh tải trùng cho kỳ báo cáo sau.
      </p>
      <button 
        onClick={handleExport}
        disabled={loading}
        className="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-8 rounded shadow-md transition-colors disabled:opacity-50"
      >
        {loading ? "Đang xử lý tạo file..." : "📥 Tải xuống File Excel"}
      </button>
    </div>
  );
};