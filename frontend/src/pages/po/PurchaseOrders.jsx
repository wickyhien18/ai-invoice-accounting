import React, { useState, useEffect } from "react";
import { api } from "../../api/client.js";
import Pagination from "../../components/Pagination.jsx";

export default function PurchaseOrders() {
  const [pos, setPos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  
  const [showForm, setShowForm] = useState(false);
  const [poNumber, setPoNumber] = useState("");
  const [vendor, setVendor] = useState("");
  const [amount, setAmount] = useState("");

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const fetchPOs = () => {
    setLoading(true);
    api("/api/purchase-orders")
      .then((res) => {
        setPos(res?.data || res || []);
        setCurrentPage(1);
      })
      .catch((err) => console.error("Lỗi tải data PO:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchPOs(); }, []);
  useEffect(() => { setCurrentPage(1); }, [searchQuery]);

  const removeAccents = (str) => {
    return str ? str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase() : "";
  };

  const filteredPOs = pos.filter(po => {
    if (!searchQuery.trim()) return true;
    const query = removeAccents(searchQuery);
    const v = removeAccents(po.vendor);
    const num = po.po_number ? String(po.po_number).toLowerCase() : "";
    return v.includes(query) || num.includes(query);
  });

  const handleCreatePO = (e) => {
    e.preventDefault();
    if (!poNumber || !vendor || !amount) { alert("Vui lòng điền đầy đủ thông tin PO!"); return; }
    const payload = { po_number: poNumber.trim(), vendor: vendor.trim(), order_date: new Date().toISOString().split('T')[0], expected_amount: parseFloat(amount) };
    api("/api/purchase-orders", { method: "POST", body: payload })
      .then(() => { alert("Đã tạo PO mới thành công!"); setPoNumber(""); setVendor(""); setAmount(""); setShowForm(false); fetchPOs(); })
      .catch((err) => alert("Lỗi: " + (err.message || "Không thể tạo PO")));
  };

  const currentPOs = filteredPOs.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  if (loading) return <div className="p-8 text-center text-slate-500">Đang tải dữ liệu Đơn mua hàng...</div>;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200">
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h2 className="text-lg font-bold text-slate-800">Danh sách Đơn mua hàng (PO)</h2>
        
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="relative w-full md:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><span className="text-slate-400">🔍</span></div>
            <input type="text" placeholder="Tìm Mã PO, Nhà cung cấp..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full pl-10 pr-8 py-1.5 border border-slate-300 rounded text-sm focus:outline-none focus:border-blue-500" />
            {searchQuery && <button onClick={() => setSearchQuery("")} className="absolute inset-y-0 right-0 pr-2 flex items-center text-slate-400 hover:text-slate-600 font-bold">✕</button>}
          </div>
          
          <button onClick={() => setShowForm(!showForm)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded text-sm font-medium transition-colors whitespace-nowrap">
            {showForm ? "Đóng form" : "+ Thêm PO"}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreatePO} className="p-6 bg-slate-50 border-b border-slate-200 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div><label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Mã PO</label><input type="text" placeholder="VD: PO-2026-067" value={poNumber} onChange={(e) => setPoNumber(e.target.value)} className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"/></div>
          <div><label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Nhà cung cấp</label><input type="text" placeholder="VD: Công ty TNHH Bờ Đen" value={vendor} onChange={(e) => setVendor(e.target.value)} className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"/></div>
          <div><label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Tổng tiền dự kiến (VNĐ)</label><input type="number" placeholder="VD: 15000000" value={amount} onChange={(e) => setAmount(e.target.value)} className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"/></div>
          <div><button type="submit" className="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors shadow-sm">Lưu PO</button></div>
        </form>
      )}
      
      {filteredPOs.length === 0 ? (
        <div className="p-12 text-center text-slate-500">{searchQuery ? `Không tìm thấy PO nào chứa "${searchQuery}".` : "Chưa có Đơn mua hàng nào trong hệ thống."}</div>
      ) : (
        <div className="flex flex-col">
          <div className="overflow-x-auto">
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
                {currentPOs.map((po) => (
                  <tr key={po.po_id || po.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 text-sm text-slate-900">{po.po_id || po.id}</td>
                    <td className="px-6 py-4 text-sm font-medium text-blue-600">{po.po_number}</td>
                    <td className="px-6 py-4 text-sm text-slate-500 uppercase tracking-wide font-medium">{po.vendor}</td>
                    <td className="px-6 py-4 text-sm text-slate-500">{po.order_date}</td>
                    <td className="px-6 py-4 text-sm font-semibold text-slate-900">{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(po.expected_amount || 0)}</td>
                    <td className="px-6 py-4 text-center text-sm"><span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs font-medium">{po.status === 'dang_mo' ? 'Đang mở' : po.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination totalItems={filteredPOs.length} pageSize={pageSize} currentPage={currentPage} setPageSize={setPageSize} setCurrentPage={setCurrentPage} />
        </div>
      )}
    </div>
  );
}