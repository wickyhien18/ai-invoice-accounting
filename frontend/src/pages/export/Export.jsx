import React, { useState } from "react";
import { api } from "../../api/client.js";

export default function Export() {
  const [loading, setLoading] = useState(false);

  const handleExport = () => {
    setLoading(true);
    api("/api/exports/sheet", { method: "POST" })
      .then((res) => {
        alert(res.message);
        if (res.download_url) {
          const a = document.createElement("a");
          a.href = res.download_url;
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
      <button onClick={handleExport} disabled={loading} className="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-8 rounded shadow-md transition-colors disabled:opacity-50">
        {loading ? "Đang xử lý tạo file..." : "📥 Tải xuống File Excel"}
      </button>
    </div>
  );
}