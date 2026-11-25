import React, { useState } from "react";
import { api } from "../../api/client.js";

export default function Export() {
  const [loadingMode, setLoadingMode] = useState(null); // "24h" | "all" | null

  const handleExport = (hours = null) => {
    setLoadingMode(hours ? "24h" : "all");
    const url = hours ? `/api/exports/sheet?hours=${hours}` : "/api/exports/sheet";

    api(url, { method: "POST" })
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
        alert(
          "Lỗi xuất file: " +
            (err.message || "Hãy đảm bảo có ít nhất 1 hóa đơn hợp lệ để xuất.")
        );
      })
      .finally(() => setLoadingMode(null));
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200 p-8 max-w-2xl mx-auto mt-6 text-center">
      <h2 className="text-2xl font-bold text-slate-800 mb-4">Xuất bảng kê 01-2/GTGT</h2>
      <p className="text-slate-600 mb-8 leading-relaxed">
        Tính năng này sẽ rà soát hệ thống để gom các hóa đơn <b>Đã duyệt</b> thành một file Excel chuẩn theo mẫu 01-2/GTGT của Bộ Tài chính.<br/> 
        Bạn có thể chọn xuất nhanh các hóa đơn vừa duyệt trong <b>24 giờ qua</b> hoặc xuất toàn bộ lịch sử đã duyệt.
      </p>
      <div className="flex flex-wrap justify-center gap-4">
        <button
          onClick={() => handleExport(24)}
          disabled={loadingMode !== null}
          className="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded shadow-md transition-colors disabled:opacity-50"
        >
          {loadingMode === "24h" ? "Đang xử lý tạo file..." : "⚡ Xuất đã duyệt (24h qua)"}
        </button>
        <button
          onClick={() => handleExport(null)}
          disabled={loadingMode !== null}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded shadow-md transition-colors disabled:opacity-50"
        >
          {loadingMode === "all" ? "Đang xử lý tạo file..." : "📥 Xuất toàn bộ đã duyệt"}
        </button>
      </div>
    </div>
  );
}