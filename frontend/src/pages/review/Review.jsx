import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, fetchBlobUrl } from "../../api/client.js";
import StatusBadge from "../invoices/StatusBadge.jsx";
import { FILE_TYPE } from "../invoices/format.js";
import InvoicePicker from "./InvoicePicker.jsx";
import FileViewer from "./FileViewer.jsx";

// B3: man hinh doi chieu chia doi. Trai: file goc. Phai: cac truong da doc, to mau theo do tin cay, sua truc tiep.
export const LABEL = {
  invoice_series: "Ký hiệu", invoice_number: "Số hóa đơn", invoice_date: "Ngày lập", seller_name: "Người bán",
  mst_seller: "MST người bán", total_before_tax: "Tiền trước thuế", vat_rate: "Thuế suất (%)",
  vat_amount: "Tiền thuế", total_amount: "Tổng thanh toán",
};
// Mau khong phai dau hieu duy nhat: moi muc deu co chu ("Cao", "Trung bình", "Thấp") va phan tram.
const LEVEL = {
  green: { text: "Cao", chip: "bg-green-100 text-green-800", bar: "border-l-green-500" },
  yellow: { text: "Trung bình", chip: "bg-amber-100 text-amber-800", bar: "border-l-amber-500" },
  red: { text: "Thấp", chip: "bg-red-100 text-red-800", bar: "border-l-red-500" },
};
const SPLIT_KEY = "review.split";   // ty le chia man hinh: chi luu o trinh duyet, khong luu CSDL
const SPLIT_MIN = 25, SPLIT_MAX = 75;

function loadSplit() {
  try {
    const v = Number(localStorage.getItem(SPLIT_KEY));
    return v >= SPLIT_MIN && v <= SPLIT_MAX ? v : 50;
  } catch { return 50; }
}

function FieldRow({ f, editable, onSave }) {
  const [draft, setDraft] = useState(f.value ?? "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => setDraft(f.value ?? ""), [f.value, f.field_id]);

  const dirty = draft.trim() !== (f.value ?? "");
  const lv = LEVEL[f.confidence_level];

  async function commit(val) {
    setBusy(true); setErr("");
    try { await onSave(f, val); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }
  const id = `field-${f.field_id}`;
  return (
    <li className={`border-l-4 ${lv.bar} rounded border border-slate-200 bg-white p-3`}>
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <label htmlFor={id} className="text-sm font-medium">{LABEL[f.field_name] || f.field_name}</label>
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${lv.chip}`}
          title="Xanh ≥ 90, vàng 70 đến dưới 90, đỏ dưới 70">
          Độ tin cậy {lv.text}{f.confidence_score == null ? "" : ` · ${Math.round(f.confidence_score)}%`}
        </span>
        {f.edited && <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-800">Đã sửa</span>}
        {f.confirmed && !f.edited && <span className="rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-700">Đã xác nhận</span>}
      </div>
      <div className="flex flex-wrap gap-2">
        <input id={id} value={draft} disabled={!editable || busy} onChange={(e) => setDraft(e.target.value)}
          onBlur={() => dirty && commit(draft)}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.currentTarget.blur();
            if (e.key === "Escape") setDraft(f.value ?? "");
          }}
          className="min-w-0 flex-1 rounded border border-slate-300 bg-white p-2 text-sm text-slate-800 disabled:opacity-70" placeholder="(chưa đọc được)" />
        {editable && !f.confirmed && !dirty && (
          <button disabled={busy || f.value == null} onClick={() => commit(f.value)}
            title="Xác nhận giá trị này đúng" className="shrink-0 rounded border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-40">✓ Đúng</button>
        )}
        {editable && f.confirmed && (
          <button disabled={busy} onClick={() => commit(null)} className="shrink-0 rounded border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50">Hoàn tác</button>
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
    <section className="rounded border border-slate-200 bg-white p-3 text-sm">
      <h3 className="mb-1 font-medium">Kiểm tra sơ bộ (cập nhật sau mỗi lần sửa)</h3>
      <ul className="space-y-1">
        {rows.map(([label, ok, details]) => (
          <li key={label} className={ok === true ? "text-green-700" : ok === false ? "text-red-700" : "text-slate-500"}>
            <b>{ok === true ? "✓" : ok === false ? "✗" : "?"}</b> {label}
            {ok !== true && details.map((x) => <p key={x} className="ml-5 text-xs">{x}</p>)}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Review() {
  const [params, setParams] = useSearchParams();
  const id = params.get("id");
  const [info, setInfo] = useState(null);     // {inv, fields, editable, checks}
  const [err, setErr] = useState("");
  const [split, setSplit] = useState(loadSplit);
  const [dragging, setDragging] = useState(false);
  const box = useRef(null);
  const nav = useNavigate();
  const [ask, setAsk] = useState(false);
  const [agree, setAgree] = useState(false);
  const [goBusy, setGoBusy] = useState(false);
  const [goErr, setGoErr] = useState("");

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
  if (err) return <p className="text-sm text-red-600">{err} <button className="text-blue-700" onClick={() => setParams({})}>← Danh sách</button></p>;
  if (!info) return <p className="text-sm text-slate-500">Đang tải…</p>;

  const { inv, fields, editable, checks } = info;
  const pending = fields.filter((f) => f.confidence_level !== "green" && !f.confirmed);
  const todo = pending.length;
  const empty = pending.filter((f) => f.value == null || String(f.value).trim() === "");
  const next = `/entries?id=${inv.invoice_id}`;

  // Sang Dinh khoan: neu con truong chua du tin cay va chua xac nhan thi PHAI qua hop thoai xac nhan;
  // bam "xac nhan" se ghi nhan cac truong do la da kiem tra (nen nut "✓ Đúng" luon co tac dung that).
  function goNext() {
    if (!editable || todo === 0) return nav(next);
    setAgree(false); setGoErr(""); setAsk(true);
  }
  async function confirmAndGo() {
    setGoBusy(true); setGoErr("");
    try {
      for (const f of pending) await save(f, f.value);
      nav(next);
    } catch (e) { setGoErr(e.message); setGoBusy(false); }
  }

  return (
    <section className="mx-auto max-w-[110rem]">
      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2">
        <button className="text-sm text-blue-700 hover:underline" onClick={() => setParams({})}>← Danh sách</button>
        <h1 className="text-2xl font-bold text-slate-800">Hóa đơn #{inv.invoice_id}</h1>
        <StatusBadge status={inv.status} />
        <span className="min-w-0 truncate text-sm text-slate-600">{FILE_TYPE[inv.file_type]} · {inv.filename}</span>
        <button onClick={goNext}
          className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 sm:ml-auto sm:w-auto">
          Tiếp: Định khoản →
        </button>
      </div>
      {!editable && (
        <p className="mb-3 rounded bg-amber-50 p-2 text-sm text-amber-800">
          Hóa đơn đang ở trạng thái “{inv.status}” nên chỉ xem, không sửa được. Chỉ sửa được khi chờ xác nhận hoặc bị từ chối.
        </p>
      )}
      {inv.status === "tu_choi" && inv.reject_reason && (
        <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">Lý do từ chối: {inv.reject_reason}</p>
      )}
      <div ref={box} className="flex min-h-[32rem] flex-col gap-3 md:h-[calc(100vh-12rem)] md:flex-row md:gap-0"
        style={{ "--split": `${split}%` }}>
        <div className={`h-[32rem] overflow-hidden rounded-lg border border-slate-200 bg-white shadow md:h-auto md:w-[var(--split)] ${dragging ? "pointer-events-none" : ""}`}>
          <FileViewer invoiceId={inv.invoice_id} fileType={inv.file_type} filename={inv.filename} />
        </div>
        <div role="separator" aria-orientation="vertical" aria-label="Kéo để đổi tỷ lệ chia màn hình"
          aria-valuemin={SPLIT_MIN} aria-valuemax={SPLIT_MAX} aria-valuenow={split} tabIndex={0}
          title="Kéo hoặc dùng phím ← → để đổi tỷ lệ"
          onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); setDragging(true); }}
          onPointerMove={onDrag} onPointerUp={() => setDragging(false)} onPointerCancel={() => setDragging(false)}
          onKeyDown={(e) => {
            if (e.key === "ArrowLeft") setSplit((s) => Math.max(SPLIT_MIN, s - 5));
            if (e.key === "ArrowRight") setSplit((s) => Math.min(SPLIT_MAX, s + 5));
          }}
          className="hidden w-2 shrink-0 cursor-col-resize rounded bg-slate-200 hover:bg-blue-300 focus:bg-blue-400 md:mx-1 md:block" />
        <div className="min-w-0 space-y-3 md:flex-1 md:overflow-y-auto md:pr-1">
          <p className={`rounded p-2 text-sm ${todo ? "bg-amber-50 text-amber-800" : "bg-green-50 text-green-800"}`}>
            {todo
              ? `Còn ${todo} trường độ tin cậy chưa cao cần xem lại (sửa hoặc bấm “✓ Đúng”). Nếu bỏ qua, hệ thống sẽ yêu cầu xác nhận trước khi sang Định khoản.`
              : "Tất cả trường đã đủ tin cậy hoặc đã được xác nhận."}
          </p>
          {fields.length === 0 && <p className="text-sm text-slate-500">Hóa đơn chưa có trường nào (chưa đọc xong hoặc đọc lỗi).</p>}
          <ul className="space-y-2">
            {fields.map((f) => <FieldRow key={f.field_id} f={f} editable={editable} onSave={save} />)}
          </ul>
          <Checks c={checks} />
          <p className="text-xs text-slate-500">
            Màu: xanh ≥ 90, vàng 70 đến dưới 90, đỏ dưới 70. Giá trị máy đọc luôn được giữ lại để so sánh.
          </p>
        </div>
      </div>

      {ask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onKeyDown={(e) => e.key === "Escape" && !goBusy && setAsk(false)}>
          <div role="dialog" aria-modal="true" aria-labelledby="ask-title"
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-slate-200 bg-white p-5 shadow-xl">
            <h2 id="ask-title" className="text-lg font-bold text-slate-800">Xác nhận trước khi định khoản</h2>
            <p className="mt-1 text-sm text-slate-600">
              Còn {todo} trường độ tin cậy chưa cao và chưa được xác nhận:
            </p>
            <ul className="mt-3 space-y-1 text-sm">
              {pending.map((f) => (
                <li key={f.field_id} className="flex flex-wrap items-baseline gap-x-2 rounded border border-slate-200 px-3 py-2">
                  <b className="text-slate-800">{LABEL[f.field_name] || f.field_name}</b>
                  <span className={`rounded px-1.5 text-xs ${LEVEL[f.confidence_level].chip}`}>{LEVEL[f.confidence_level].text}</span>
                  <span className="min-w-0 flex-1 break-words text-right text-slate-700">{f.value || "(trống)"}</span>
                </li>
              ))}
            </ul>
            {empty.length > 0 ? (
              <p role="alert" className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">
                Có {empty.length} trường đang trống ({empty.map((f) => LABEL[f.field_name] || f.field_name).join(", ")}). Hãy nhập giá trị trước khi sang Định khoản.
              </p>
            ) : (
              <label className="mt-3 flex items-start gap-2 text-sm text-slate-800">
                <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-1" />
                <span>Tôi đã đối chiếu với file gốc và xác nhận các trường trên là đúng.</span>
              </label>
            )}
            {goErr && <p role="alert" className="mt-2 text-sm text-red-600">{goErr}</p>}
            <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button disabled={goBusy} onClick={() => setAsk(false)}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">Quay lại kiểm tra</button>
              <button disabled={goBusy || !agree || empty.length > 0} onClick={confirmAndGo}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40">
                {goBusy ? "Đang lưu…" : "Xác nhận & sang Định khoản"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
