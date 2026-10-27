import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom"; 
import { api, fetchBlobUrl } from "../../api/client.js";
import StatusBadge from "../invoices/StatusBadge.jsx";
import { FILE_TYPE } from "../invoices/format.js";
import InvoicePicker from "./InvoicePicker.jsx";

export const LABEL = {
  invoice_series: "Ký hiệu", invoice_number: "Số hóa đơn", invoice_date: "Ngày lập", seller_name: "Người bán",
  mst_seller: "MST người bán", total_before_tax: "Tiền trước thuế", vat_rate: "Thuế suất (%)",
  vat_amount: "Tiền thuế", total_amount: "Tổng thanh toán",
};

const LEVEL = {
  green: { text: "Cao", chip: "bg-green-100 text-green-800", bar: "border-l-green-500" },
  yellow: { text: "Trung bình", chip: "bg-amber-100 text-amber-800", bar: "border-l-amber-500" },
  red: { text: "Thấp", chip: "bg-red-100 text-red-800", bar: "border-l-red-500" },
  unknown: { text: "Chưa rõ", chip: "bg-slate-200 text-slate-700", bar: "border-l-slate-400" },
};

function levelOf(f) {
  if (f.confidence_level !== "unknown" && LEVEL[f.confidence_level]) return f.confidence_level;
  const s = f.confidence_score;
  if (s == null || Number.isNaN(Number(s))) return "unknown";
  return s >= 90 ? "green" : s >= 70 ? "yellow" : "red";
}
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
  const lv = LEVEL[levelOf(f)];
  
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

export default function Review() {
  const [params, setParams] = useSearchParams();
  const id = params.get("id");
  const navigate = useNavigate(); 
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  const [split, setSplit] = useState(loadSplit);
  const [dragging, setDragging] = useState(false);
  const box = useRef(null);

  const [showRedModal, setShowRedModal] = useState(false);
  const [showYellowModal, setShowYellowModal] = useState(false);

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

  const { inv, editable, checks } = info;
  const fields = info.fields || [];
  
  const unconfirmedFields = fields.filter((f) => !f.confirmed);
  const hasRed = unconfirmedFields.some(f => levelOf(f) === "red");
  const hasYellow = unconfirmedFields.some(f => levelOf(f) === "yellow" || levelOf(f) === "unknown");
  const todo = fields.filter((f) => levelOf(f) !== "green" && !f.confirmed).length;

  const handleNextStep = () => {
    if (hasRed) {
      setShowRedModal(true);
      return;
    }
    
    if (hasYellow) {
      setShowYellowModal(true);
      return;
    }

    navigate(`/entries?id=${inv.invoice_id}`);
  };

  return (
    <section className="relative">

      {/* POP-UP LỖI NGHIÊM TRỌNG (ĐỎ) - TRẢ VỀ STYLE CHUẨN */}
      {showRedModal && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm transition-opacity">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 border-4 border-red-50 shadow-inner">
                <span className="text-3xl font-bold text-red-600">✕</span>
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Cảnh báo nghiêm trọng</h3>
              <p className="text-slate-600 mb-6 leading-relaxed text-sm">
                Vẫn còn trường dữ liệu có độ tin cậy <b className="text-red-600">THẤP (Đỏ)</b> chưa được xác nhận. Vui lòng tự gõ sửa lại hoặc bấm <b>'✓ Đúng'</b> trước khi đi tiếp để tránh sai sót định khoản!
              </p>
              <div className="flex justify-center">
                <button 
                  onClick={() => setShowRedModal(false)} 
                  className="px-6 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-bold transition-colors shadow-md w-full">
                  Đã hiểu & Quay lại sửa
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* POP-UP CẢNH BÁO XÁC NHẬN (VÀNG) - TRẢ VỀ STYLE CHUẨN */}
      {showYellowModal && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm transition-opacity">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 text-center">
              <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4 border-4 border-amber-50 shadow-inner">
                <span className="text-3xl font-bold text-amber-600">!</span>
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Xác nhận chuyển trang</h3>
              <p className="text-slate-600 mb-8 leading-relaxed text-sm">
                Vẫn còn một số trường dữ liệu chưa được xác nhận (độ tin cậy <b className="text-amber-600">Trung bình</b>). Bạn có chắc chắn thông tin trên hóa đơn đã chính xác 100% để tiếp tục sang Định khoản?
              </p>
              <div className="flex gap-3 justify-center">
                <button 
                  onClick={() => setShowYellowModal(false)} 
                  className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded-lg font-bold transition-colors w-1/2">
                  Hủy bỏ
                </button>
                <button 
                  onClick={() => { setShowYellowModal(false); navigate(`/entries?id=${inv.invoice_id}`); }} 
                  className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold transition-colors shadow-md w-1/2">
                  Tiếp tục
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
        <button className="text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1" onClick={() => setParams({})}>← Trở lại</button>
        <div className="w-px h-4 bg-slate-300 mx-1"></div>
        <h1 className="text-xl font-bold text-slate-800">Hóa đơn #{inv.invoice_id}</h1>
        <StatusBadge status={inv.status} />
        <span className="text-slate-500 font-medium bg-slate-100 px-2 py-1 rounded">{FILE_TYPE[inv.file_type]} · {inv.filename}</span>
        
        <button 
          onClick={handleNextStep}
          className={`ml-auto rounded-lg px-4 py-1.5 font-medium shadow-sm transition-colors ${hasRed ? 'bg-red-600 hover:bg-red-700 text-white' : 'bg-blue-600 hover:bg-blue-700 text-white'}`}
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