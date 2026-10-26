import React, { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import Placeholder from "../components/Placeholder.jsx";
import { api, fetchBlobUrl } from "../api/client.js";
import UploadPage from "./invoices/Upload.jsx";
import StatusBadge from "./invoices/StatusBadge.jsx";
import { FILE_TYPE } from "./invoices/format.js";
import InvoicePicker from "./review/InvoicePicker.jsx"; // Đảm bảo đường dẫn này đúng

export const Upload = UploadPage;
export { default as Entries } from "./entries/Entries.jsx";
export { default as Catalog } from "./catalog/Catalog.jsx";

// ---------------------------------------------------------
// COMPONENT PHÂN TRANG DÙNG CHUNG (TÁI SỬ DỤNG CHO MỌI BẢNG)
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


// ---------------------------------------------------------
// COMPONENT REVIEW (TRANG KIỂM TRA - ĐÃ CẬP NHẬT LOGIC CHẶN)
// ---------------------------------------------------------
export const LABEL = {
  invoice_series: "Ký hiệu", invoice_number: "Số hóa đơn", invoice_date: "Ngày lập", seller_name: "Người bán",
  mst_seller: "MST người bán", total_before_tax: "Tiền trước thuế", vat_rate: "Thuế suất (%)",
  vat_amount: "Tiền thuế", total_amount: "Tổng thanh toán",
};

const LEVEL = {
  green: { text: "Cao", chip: "bg-green-100 text-green-800", bar: "border-l-green-500" },
  yellow: { text: "Trung bình", chip: "bg-amber-100 text-amber-800", bar: "border-l-amber-500" },
  red: { text: "Thấp", chip: "bg-red-100 text-red-800", bar: "border-l-red-500" },
};
const SPLIT_KEY = "review.split";
const SPLIT_MIN = 25, SPLIT_MAX = 75;

function loadSplit() {
  try {
    const v = Number(localStorage.getItem(SPLIT_KEY));
    return v >= SPLIT_MIN && v <= SPLIT_MAX ? v : 50;
  } catch { return 50; }
}

function Viewer({ invoiceId, fileType, frozen }) {
  const [src, setSrc] = useState(null);
  const [text, setText] = useState(null);
  const [err, setErr] = useState("");
  
  const [zoom, setZoom] = useState(1);
  const [rotate, setRotate] = useState(0);

  useEffect(() => {
    let dead = false, url = null;
    setSrc(null); setText(null); setErr(""); setZoom(1); setRotate(0);
    fetchBlobUrl(`/api/invoices/${invoiceId}/file`).then(async (u) => {
      url = u;
      if (dead) return URL.revokeObjectURL(u);
      if (fileType === "xml") setText(await (await fetch(u)).text());
      else setSrc(u);
    }).catch((e) => !dead && setErr(e.message));
    return () => { dead = true; if (url) URL.revokeObjectURL(url); };
  }, [invoiceId, fileType]);

  if (err) return <p className="p-4 text-sm text-red-600">Không mở được file gốc: {err}</p>;
  if (!src && text === null) return <p className="p-4 text-sm text-slate-500">Đang tải file gốc…</p>;
  if (text !== null) return <pre className="h-full overflow-auto whitespace-pre-wrap break-all p-3 text-xs">{text}</pre>;
  if (fileType === "pdf") {
    return <iframe title="Hóa đơn gốc (PDF)" src={src} className={`h-full w-full ${frozen ? "pointer-events-none" : ""}`} />;
  }
  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b bg-slate-50 px-3 py-2 text-sm shadow-sm z-10">
        <div className="flex items-center bg-white border rounded shadow-sm">
          <button className="px-2.5 py-1 hover:bg-slate-100 text-slate-700 border-r" onClick={() => setZoom((z) => Math.max(0.25, +(z - 0.25).toFixed(2)))} aria-label="Thu nhỏ">−</button>
          <span className="w-14 text-center tabular-nums font-medium text-slate-700">{Math.round(zoom * 100)}%</span>
          <button className="px-2.5 py-1 hover:bg-slate-100 text-slate-700 border-l" onClick={() => setZoom((z) => Math.min(4, +(z + 0.25).toFixed(2)))} aria-label="Phóng to">+</button>
        </div>
        <button className="rounded border bg-white px-3 py-1 text-slate-700 hover:bg-slate-100 shadow-sm" onClick={() => {setZoom(1); setRotate(0);}}>Vừa khung</button>
        <div className="w-px h-5 bg-slate-300 mx-1"></div>
        <button className="rounded border bg-white px-3 py-1 text-slate-700 hover:bg-slate-100 shadow-sm flex items-center gap-1" onClick={() => setRotate((r) => r - 90)}>↺ Xoay trái</button>
        <button className="rounded border bg-white px-3 py-1 text-slate-700 hover:bg-slate-100 shadow-sm flex items-center gap-1" onClick={() => setRotate((r) => r + 90)}>↻ Xoay phải</button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto bg-slate-200 relative">
        <div className="flex min-h-full items-center justify-center p-4">
          <img src={src} alt="Hóa đơn gốc" 
               style={{ width: `${zoom * 100}%`, maxWidth: "none", transform: `rotate(${rotate}deg)`, transition: "transform 0.2s ease-in-out" }} 
               className="block shadow-md bg-white" />
        </div>
      </div>
    </div>
  );
}

function FieldRow({ f, editable, onSave }) {
  const [draft, setDraft] = useState(f.value ?? "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => setDraft(f.value ?? ""), [f.value, f.field_id]);

  const dirty = draft.trim() !== (f.value ?? "");
  const lv = LEVEL[f.confidence_level];
  const isUpper = ["seller_name", "invoice_series", "mst_seller"].includes(f.field_name);

  async function commit(val) {
    setBusy(true); setErr("");
    try { await onSave(f, val); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }
  const id = `field-${f.field_id}`;
  return (
    <li className={`border-l-4 ${lv.bar} rounded border bg-white p-3 shadow-sm hover:shadow transition-shadow`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <label htmlFor={id} className="text-sm font-bold text-slate-700">{LABEL[f.field_name] || f.field_name}</label>
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${lv.chip}`} title="Xanh ≥ 90, vàng 70 đến dưới 90, đỏ dưới 70">
          Độ tin cậy {lv.text}{f.confidence_score == null ? "" : ` · ${Math.round(f.confidence_score)}%`}
        </span>
        {f.edited && <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-800 font-medium">Đã sửa</span>}
        {f.confirmed && !f.edited && <span className="rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-700 font-medium">Đã xác nhận</span>}
      </div>
      <div className="flex gap-2">
        <input id={id} value={draft} disabled={!editable || busy} onChange={(e) => setDraft(e.target.value)}
          onBlur={() => dirty && commit(draft)}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.currentTarget.blur();
            if (e.key === "Escape") setDraft(f.value ?? "");
          }}
          className={`w-full rounded border p-2 text-sm disabled:opacity-70 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all ${isUpper ? 'uppercase font-semibold text-slate-900' : 'text-slate-800'}`} 
          placeholder="(chưa đọc được)" />
        {editable && !f.confirmed && !dirty && (
          <button disabled={busy || f.value == null} onClick={() => commit(f.value)}
            title="Xác nhận giá trị này đúng" className="shrink-0 rounded border border-green-500 text-green-700 bg-green-50 hover:bg-green-100 px-3 text-sm font-medium disabled:opacity-40 transition-colors">✓ Đúng</button>
        )}
        {editable && f.confirmed && (
          <button disabled={busy} onClick={() => commit(null)} className="shrink-0 rounded border px-3 text-sm font-medium hover:bg-slate-100 transition-colors">Hoàn tác</button>
        )}
      </div>
      {f.edited && <p className="mt-1 text-xs text-slate-500">Máy đọc được: {f.extracted_value ?? "(trống)"}</p>}
      {err && <p role="alert" className="mt-1 text-xs text-red-600">{err}</p>}
    </li>
  );
}

function Checks({ c }) {
  if (!c) return null;
  const d = c.issue_details || { mst: [], totals: [], duplicate: [] };
  const rows = [["MST người bán đúng định dạng", c.mst_valid, d.mst],
    ["Tiền trước thuế + thuế = tổng thanh toán", c.total_matches, d.totals],
    ["Không trùng hóa đơn đã có", !c.duplicate, d.duplicate]];
  return (
    <section className="rounded border bg-white p-3 text-sm shadow-sm">
      <h3 className="mb-2 font-bold text-slate-700 border-b pb-1">Kiểm tra sơ bộ tự động</h3>
      <ul className="space-y-1.5">
        {rows.map(([label, ok, details]) => (
          <li key={label} className={ok === true ? "text-green-700 font-medium" : ok === false ? "text-red-700 font-medium" : "text-slate-500"}>
            <b className="inline-block w-5">{ok === true ? "✓" : ok === false ? "✗" : "?"}</b> {label}
            {ok !== true && details.map((x) => <p key={x} className="ml-5 mt-0.5 text-xs text-red-600">{x}</p>)}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Review() {
  const [params, setParams] = useSearchParams();
  const id = params.get("id");
  const navigate = useNavigate(); // Hook dùng để chuyển trang
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  const [split, setSplit] = useState(loadSplit);
  const [dragging, setDragging] = useState(false);
  const box = useRef(null);

  useEffect(() => { try { localStorage.setItem(SPLIT_KEY, String(split)); } catch { /* bi chan: bo qua */ } }, [split]);

  useEffect(() => {
    if (!id) return;
    let dead = false;
    setInfo(null); setErr("");
    Promise.all([api(`/api/invoices/${id}`), api(`/api/invoices/${id}/fields`)])
      .then(([i, f]) => !dead && setInfo({ inv: i.data, checks: i.data.checks, fields: f.data, editable: f.editable }))
      .catch((e) => !dead && setErr(e.message));
    return () => { dead = true; };
  }, [id]);

  const save = useCallback(async (f, value) => {
    const r = await api(`/api/invoices/${id}/fields/${f.field_id}`, { method: "PATCH", body: { final_value: value } });
    setInfo((s) => ({ ...s, inv: { ...s.inv, ...r.invoice }, checks: r.checks,
      fields: s.fields.map((x) => (x.field_id === f.field_id ? r.data : x)) }));
  }, [id]);

  function onDrag(e) {
    if (!dragging || !box.current) return;
    const r = box.current.getBoundingClientRect();
    setSplit(Math.min(SPLIT_MAX, Math.max(SPLIT_MIN, Math.round(((e.clientX - r.left) / r.width) * 100))));
  }

  if (!id) return <InvoicePicker title="Kiểm tra trường trích xuất"
    hint="Chọn một hóa đơn để đối chiếu file gốc với các trường máy đọc được, rồi sửa những chỗ sai." />;
  if (err) return <p className="text-sm text-red-600">{err} <button className="text-blue-700 underline" onClick={() => setParams({})}>← Trở về danh sách</button></p>;
  if (!info) return <div className="p-8 text-center text-slate-500 font-medium">Đang tải dữ liệu hóa đơn...</div>;

  const { inv, fields, editable, checks } = info;
  // FIX VẤN ĐỀ 2: Đếm số trường cần xác nhận
  const todo = fields.filter((f) => f.confidence_level !== "green" && !f.confirmed).length;

  const handleNextStep = () => {
    if (todo > 0) {
      alert(`CẢNH BÁO: Vẫn còn ${todo} trường dữ liệu chưa được xác nhận!\n\nVui lòng bấm "✓ Đúng" hoặc tự gõ sửa lại các trường bị cảnh báo (vàng/đỏ) trước khi chuyển sang bước Định khoản.`);
    } else {
      navigate(`/entries?id=${inv.invoice_id}`);
    }
  };

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
        <button className="text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1" onClick={() => setParams({})}>← Trở lại</button>
        <div className="w-px h-4 bg-slate-300 mx-1"></div>
        <h1 className="text-xl font-bold text-slate-800">Hóa đơn #{inv.invoice_id}</h1>
        <StatusBadge status={inv.status} />
        <span className="text-slate-500 font-medium bg-slate-100 px-2 py-1 rounded">{FILE_TYPE[inv.file_type]} · {inv.filename}</span>
        
        {/* FIX VẤN ĐỀ 2: Đổi Link thành Button để kiểm tra điều kiện todo === 0 trước khi sang trang */}
        <button 
          onClick={handleNextStep}
          className={`ml-auto rounded-lg px-4 py-1.5 font-medium shadow-sm transition-colors ${todo > 0 ? 'bg-slate-400 text-white cursor-not-allowed hover:bg-slate-500' : 'bg-blue-600 hover:bg-blue-700 text-white'}`}
        >
          Tiếp: Định khoản →
        </button>
      </div>
      {!editable && (
        <p className="mb-4 rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800 font-medium flex items-center gap-2">
          <span>⚠️</span> Hóa đơn đang ở trạng thái “{inv.status}” nên chỉ xem, không sửa được. Chỉ sửa được khi "Chờ xác nhận" hoặc "Bị từ chối".
        </p>
      )}
      {inv.status === "tu_choi" && inv.reject_reason && (
        <p className="mb-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700 font-medium flex items-center gap-2">
          <span>❌</span> Lý do từ chối: {inv.reject_reason}
        </p>
      )}
      <div ref={box} className="flex min-h-[32rem] flex-col gap-4 md:h-[calc(100vh-12rem)] md:flex-row md:gap-0"
        style={{ "--split": `${split}%` }}>
        <div className="h-[28rem] overflow-hidden rounded-lg border shadow-sm bg-white md:h-auto md:w-[var(--split)]">
          <Viewer invoiceId={inv.invoice_id} fileType={inv.file_type} frozen={dragging} />
        </div>
        <div role="separator" aria-orientation="vertical" aria-label="Kéo để đổi tỷ lệ chia màn hình"
          aria-valuemin={SPLIT_MIN} aria-valuemax={SPLIT_MAX} aria-valuenow={split} tabIndex={0}
          title="Kéo hoặc dùng phím ← → để đổi tỷ lệ"
          onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); setDragging(true); }}
          onPointerMove={onDrag} onPointerUp={() => setDragging(false)} onPointerCancel={() => setDragging(false)}
          className="hidden w-3 shrink-0 cursor-col-resize hover:bg-blue-200 active:bg-blue-400 md:mx-1 md:block transition-colors rounded-full" />
        <div className="min-w-0 space-y-4 overflow-y-auto md:flex-1 pl-1 pr-2">
          <p className={`rounded-lg border p-3 text-sm font-medium shadow-sm ${todo ? "bg-amber-50 border-amber-200 text-amber-800" : "bg-green-50 border-green-200 text-green-800"}`}>
            {todo ? `🎯 Còn ${todo} trường độ tin cậy chưa cao cần xem lại (sửa hoặc bấm “✓ Đúng”).` : "✅ Tất cả trường đã đủ tin cậy hoặc đã được xác nhận."}
          </p>
          {fields.length === 0 && <p className="text-sm text-slate-500 italic p-4 text-center border rounded-lg bg-slate-50">Hóa đơn chưa có trường nào (chưa đọc xong hoặc đọc lỗi).</p>}
          <ul className="space-y-3">
            {fields.map((f) => <FieldRow key={f.field_id} f={f} editable={editable} onSave={save} />)}
          </ul>
          <Checks c={checks} />
          <p className="text-xs text-slate-500 bg-slate-50 p-2 rounded border">
            * Màu sắc: Xanh ≥ 90, Vàng 70 đến dưới 90, Đỏ dưới 70. Giá trị máy đọc gốc luôn được giữ lại ẩn bên trong để so sánh.
          </p>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------
// CỬA SỔ ĐỐI CHIẾU NHANH DÀNH CHO KẾ TOÁN TRƯỞNG
// ---------------------------------------------------------
const QuickReviewModal = ({ invoiceId, onClose, onApprove, onReject }) => {
  const [inv, setInv] = useState(null);
  const [entries, setEntries] = useState(null);
  const [fileSrc, setFileSrc] = useState(null);
  const [xmlText, setXmlText] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let dead = false;
    let url = null;
    setLoading(true);

    Promise.all([
      api(`/api/invoices/${invoiceId}`),
      api(`/api/invoices/${invoiceId}/journal-entries`).catch(() => ({ data: [] })),
      fetchBlobUrl(`/api/invoices/${invoiceId}/file`).catch(() => null)
    ]).then(async ([invRes, entriesRes, blobUrl]) => {
      if (dead) {
        if (blobUrl) URL.revokeObjectURL(blobUrl);
        return;
      }
      
      setInv(invRes.data);
      setEntries(entriesRes.data || []);
      url = blobUrl;
      
      if (invRes.data.file_type === "xml" && blobUrl) {
        const txt = await (await fetch(blobUrl)).text();
        setXmlText(txt);
      } else {
        setFileSrc(blobUrl);
      }
      setLoading(false);
    }).catch(err => {
      console.error("Lỗi tải chi tiết:", err);
      setLoading(false);
    });

    return () => {
      dead = true;
      if (url) URL.revokeObjectURL(url);
    };
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

  // FIX LỖI HIỂN THỊ UNICODE CHO MÁY BÊN HIỂN BẰNG NFC NORMALIZATION
  const normalizeText = (text) => text ? text.normalize("NFC") : "—";

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-slate-100 animate-in fade-in zoom-in-95 duration-200">
      <div className="flex justify-between items-center bg-white px-6 py-3 border-b shadow-sm">
         <div className="flex items-center gap-4">
           <h2 className="text-xl font-bold text-slate-800">Đối chiếu nhanh: Hóa đơn #{inv.invoice_id}</h2>
           {inv.is_anomaly && <span className="bg-red-600 text-white px-2 py-0.5 rounded text-xs font-bold shadow-sm">⚠️ Rủi ro cao</span>}
         </div>
         <div className="flex gap-3">
            {/* Bỏ hàm onClose() ở đây để modal không biến mất khi pop-up xác nhận hiện lên */}
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
         <div className="w-1/2 border-r border-slate-300 bg-slate-200 flex flex-col relative">
            <div className="absolute top-0 left-0 right-0 bg-white/90 backdrop-blur-sm p-2 text-sm font-semibold text-slate-700 border-b z-10 flex justify-between shadow-sm">
              <span>📄 File gốc ({inv.file_type?.toUpperCase()})</span>
              <span className="text-slate-500 font-normal truncate max-w-[60%]">{inv.filename}</span>
            </div>
            <div className="flex-1 overflow-auto pt-11 bg-white">
              {xmlText ? <pre className="p-4 text-xs bg-white min-h-full whitespace-pre-wrap break-all">{xmlText}</pre> :
               fileSrc && inv.file_type === "pdf" ? <iframe src={fileSrc} className="w-full h-full bg-white" title="PDF Viewer" /> :
               fileSrc ? <img src={fileSrc} className="max-w-full m-auto block bg-white shadow-sm" alt="Invoice" /> :
               <div className="p-4 text-slate-500 flex h-full items-center justify-center bg-white">Không tải được file gốc</div>
              }
            </div>
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
                 {/* ÉP HIỂN THỊ UNICODE NFC CHỐNG LỖI MÁY HIỂN */}
                 <strong className="text-xl text-blue-700 uppercase font-bold tracking-wide">{normalizeText(inv.seller_name)}</strong>
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

            {inv.checks && (
               <div className="mt-8">
                 <h3 className="font-bold text-slate-800 text-lg mb-4 border-b pb-2">Kết quả kiểm tra tự động</h3>
                 <ul className="space-y-3 text-sm">
                    <li className={`flex items-start gap-2 ${inv.checks.mst_valid ? 'text-green-700' : 'text-red-700'}`}>
                      <b className="mt-0.5">{inv.checks.mst_valid ? '✓' : '✗'}</b> 
                      <span>{inv.checks.mst_valid ? 'MST hợp lệ, đúng định dạng.' : 'MST không đúng định dạng!'}</span>
                    </li>
                    <li className={`flex items-start gap-2 ${inv.checks.total_matches ? 'text-green-700' : 'text-red-700'}`}>
                      <b className="mt-0.5">{inv.checks.total_matches ? '✓' : '✗'}</b> 
                      <span>{inv.checks.total_matches ? 'Khớp tổng tiền (Tiền trước thuế + Thuế = Tổng).' : 'Cảnh báo: Tổng tiền tính toán KHÔNG khớp!'}</span>
                    </li>
                    <li className={`flex items-start gap-2 ${!inv.checks.duplicate ? 'text-green-700' : 'text-red-700'}`}>
                      <b className="mt-0.5">{!inv.checks.duplicate ? '✓' : '✗'}</b> 
                      <span>{!inv.checks.duplicate ? 'Không phát hiện trùng lặp hóa đơn.' : 'Cảnh báo: Trùng lặp với hóa đơn đã có trong hệ thống!'}</span>
                    </li>
                 </ul>
               </div>
            )}
         </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------
// Nhiệm vụ C3: Luồng duyệt & Hàng chờ duyệt
// ---------------------------------------------------------
export const Approvals = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  const [rejectingId, setRejectingId] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  
  // State lưu hóa đơn đang được chọn để xác nhận Duyệt 2 Lần
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

  useEffect(() => {
    fetchApprovals();
  }, []);

  // Gọi Pop-up Xác nhận Duyệt
  const handleConfirmApprove = (id) => {
    setConfirmApproveId(id);
  };

  // Thực thi Duyệt Chính Thức sau khi Đồng ý
  const executeApprove = () => {
    if (!confirmApproveId) return;
    setSubmitting(true);
    api(`/api/invoices/${confirmApproveId}/approve`, { method: "POST" })
      .then(() => {
        alert(`Hóa đơn ${confirmApproveId} đã được phê duyệt!`);
        if (rejectingId === confirmApproveId) closeRejectForm(); 
        if (viewingId === confirmApproveId) setViewingId(null);
        setConfirmApproveId(null); // Đóng pop-up
        fetchApprovals();
      })
      .catch(() => alert("Lỗi khi duyệt hóa đơn. Bạn có đúng quyền Kế Toán Trưởng không?"))
      .finally(() => setSubmitting(false));
  };

  const openRejectForm = (id) => {
    setRejectingId(id);
    setRejectReason("");
  };

  const closeRejectForm = () => {
    setRejectingId(null);
    setRejectReason("");
  };

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
        if (viewingId === rejectingId) setViewingId(null);
        fetchApprovals();
      })
      .catch(() => alert("Lỗi khi từ chối hóa đơn."))
      .finally(() => setSubmitting(false));
  };

  const scrollToInvoice = (id) => {
    setShowAnomalyModal(false);
    
    const index = invoices.findIndex(inv => (inv.invoice_id || inv.id) === id);
    if (index !== -1) {
      const targetPage = Math.floor(index / pageSize) + 1;
      if (currentPage !== targetPage) {
        setCurrentPage(targetPage);
      }
      
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

  const currentInvoices = invoices.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  if (loading) return <div className="p-8 text-center text-slate-500">Đang tải dữ liệu...</div>;

  // FIX LỖI HIỂN THỊ UNICODE CHO MÁY BÊN HIỂN BẰNG NFC NORMALIZATION
  const normalizeText = (text) => text ? text.normalize("NFC") : "—";

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200 relative">
      
      {/* CỬA SỔ POP-UP XÁC NHẬN DUYỆT HÓA ĐƠN (Z-INDEX CAO NHẤT 70) */}
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
                <button 
                  disabled={submitting}
                  onClick={() => setConfirmApproveId(null)} 
                  className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-bold transition-colors w-1/2">
                  Hủy bỏ
                </button>
                <button 
                  disabled={submitting}
                  onClick={executeApprove} 
                  className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold transition-colors shadow-md w-1/2 flex justify-center items-center">
                  {submitting ? "Đang xử lý..." : "Đồng ý Duyệt"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CỬA SỔ ĐỐI CHIẾU NHANH (Z-INDEX 60) */}
      {viewingId && (
        <QuickReviewModal 
          invoiceId={viewingId} 
          onClose={() => setViewingId(null)} 
          onApprove={handleConfirmApprove} 
          onReject={openRejectForm} 
        />
      )}

      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-bold text-slate-800">Hàng chờ duyệt</h2>
          
          <button 
            onClick={() => setShowAnomalyModal(true)}
            className="flex items-center gap-2 bg-orange-100 hover:bg-orange-200 text-orange-800 border border-orange-200 px-3 py-1.5 rounded text-sm font-semibold transition-colors shadow-sm"
          >
            Cảnh báo rủi ro ({invoices.filter(i => i.is_anomaly).length})
          </button>
        </div>
        {rejectingId && (
          <button 
            onClick={closeRejectForm}
            className="text-sm font-medium text-slate-500 hover:text-slate-700 bg-white border border-slate-300 px-3 py-1.5 rounded transition-colors"
          >
            Đóng form
          </button>
        )}
      </div>

      {showAnomalyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl overflow-hidden border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
              <h3 className="text-lg font-bold text-red-700 flex items-center gap-2">
                Danh sách Hóa đơn có rủi ro cao
              </h3>
              <button onClick={() => setShowAnomalyModal(false)} className="text-slate-400 hover:text-slate-700 text-xl font-bold">
                ✕
              </button>
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
                          <div className="font-bold text-red-600">
                            {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(inv.total_amount || inv.total || 0)}
                          </div>
                          <button 
                            onClick={() => scrollToInvoice(inv.invoice_id || inv.id)}
                            className="bg-blue-100 hover:bg-blue-200 text-blue-700 px-3 py-1 rounded text-xs font-bold transition-colors shadow-sm flex items-center gap-1"
                            title="Đóng cửa sổ và cuộn tới dòng hóa đơn này"
                          >
                            Đi tới ➔
                          </button>
                        </div>
                      </div>
                      <div className="text-sm text-slate-700 mb-1">
                        <span className="font-semibold">Nhà cung cấp:</span> {inv.seller_name || inv.vendor || "N/A"}
                      </div>
                      <div className="text-sm text-red-700 bg-white inline-block px-2 py-1 rounded border border-red-100 font-medium">
                        {inv.anomaly_reason}
                      </div>
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
                    <tr 
                      id={`invoice-row-${currentId}`}
                      key={currentId} 
                      className={`
                        ${isHighlighted ? "bg-blue-50 ring-2 ring-blue-400 ring-inset shadow-inner transition-all duration-300" : 
                          isRejecting ? "bg-red-100 transition-colors" : 
                          inv.is_anomaly ? "bg-red-50 hover:bg-red-100 transition-colors" : 
                          "hover:bg-slate-50 transition-colors"}
                      `}
                    >
                      <td className={`px-6 py-4 text-sm ${inv.is_anomaly ? "text-red-700 font-bold" : "text-slate-900"}`}>{currentId}</td>
                      <td className={`px-6 py-4 text-sm font-medium ${inv.is_anomaly ? "text-red-600" : "text-blue-600"}`}>{inv.invoice_number || "N/A"}</td>
                      <td className="px-6 py-4 text-sm text-slate-500">
                        {/* FIX LỖI HIỂN THỊ TRÊN BẢNG DUYỆT BẰNG NFC */}
                        <div className={`font-medium uppercase tracking-wide ${inv.is_anomaly ? "text-red-700" : "text-slate-700"}`}>
                          {normalizeText(inv.seller_name || inv.vendor)}
                          {inv.is_anomaly && (
                            <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-red-600 text-white shadow-sm">
                              ⚠️ Bất thường
                            </span>
                          )}
                        </div>
                      </td>
                      <td className={`px-6 py-4 text-sm font-semibold ${inv.is_anomaly ? "text-red-700" : "text-slate-900"}`}>
                        {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(inv.total_amount || inv.total || 0)}
                      </td>
                      
                      <td className="px-6 py-4 text-center text-sm font-medium whitespace-nowrap">
                        <button 
                          onClick={() => setViewingId(currentId)} 
                          className="text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 px-3 py-1.5 rounded mr-2 shadow-sm transition-all"
                          title="Mở ảnh gốc để đối chiếu"
                        >
                          👁️ Kiểm tra
                        </button>
                        <button 
                          onClick={() => handleConfirmApprove(currentId)} 
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
          </div>
          
          <Pagination 
            totalItems={invoices.length}
            pageSize={pageSize}
            currentPage={currentPage}
            setPageSize={setPageSize}
            setCurrentPage={setCurrentPage}
          />
        </div>
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

  const currentPOs = pos.slice((currentPage - 1) * pageSize, currentPage * pageSize);

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
          </div>
          
          <Pagination 
            totalItems={pos.length}
            pageSize={pageSize}
            currentPage={currentPage}
            setPageSize={setPageSize}
            setCurrentPage={setCurrentPage}
          />
        </div>
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