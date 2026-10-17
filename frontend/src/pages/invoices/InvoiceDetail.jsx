import { useEffect, useState } from "react";
import { api, fetchBlobUrl } from "../../api/client.js";
import StatusBadge from "./StatusBadge.jsx";
import { dateVN, FILE_TYPE, money } from "./format.js";

const ROWS = [
  ["invoice_series", "Ký hiệu"], ["invoice_number", "Số hóa đơn"], ["invoice_date", "Ngày lập", dateVN],
  ["seller_name", "Người bán"], ["mst_seller", "MST người bán"],
  ["total_before_tax", "Tiền trước thuế", money], ["vat_rate", "Thuế suất (%)"],
  ["vat_amount", "Tiền thuế", money], ["total_amount", "Tổng thanh toán", money],
];

export default function InvoiceDetail({ invoiceId, onClose, onChanged }) {
  const [inv, setInv] = useState(null);
  const [check, setCheck] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = () => api(`/api/invoices/${invoiceId}`).then((r) => { setInv(r.data); setCheck(r.data.checks); })
    .catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [invoiceId]);

  async function run(fn) {
    setBusy(true); setErr("");
    try { await fn(); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  const runCheck = () => run(async () => setCheck((await api(`/api/invoices/${invoiceId}/check`, { method: "POST" })).data));
  const reprocess = () => run(async () => { await api(`/api/invoices/${invoiceId}/reprocess`, { method: "POST" }); onChanged?.(); await load(); });
  // Chung tu tai chinh can dang nhap: lay blob kem token roi mo tab moi
  const openFile = () => run(async () => window.open(await fetchBlobUrl(`/api/invoices/${invoiceId}/file`), "_blank", "noopener"));

  return (
    <div className="fixed inset-0 z-10 flex justify-end bg-black/30" onClick={onClose}>
      <aside className="h-full w-full max-w-md overflow-y-auto bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Hóa đơn #{invoiceId}</h2>
          <button className="text-slate-500" onClick={onClose} aria-label="Đóng">✕</button>
        </div>
        {err && <p className="mb-2 rounded bg-red-50 p-2 text-sm text-red-700">{err}</p>}
        {!inv ? <p className="text-sm text-slate-500">Đang tải…</p> : (
          <>
            <p className="mb-3 flex items-center gap-2 text-sm text-slate-600">
              <StatusBadge status={inv.status} /> {FILE_TYPE[inv.file_type]} · {inv.filename}
            </p>
            <dl className="mb-4 grid grid-cols-[9rem_1fr] gap-y-1 text-sm">
              {ROWS.map(([k, label, fmt]) => (
                <div key={k} className="contents">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="break-words">{inv[k] == null ? "—" : fmt ? fmt(inv[k]) : inv[k]}</dd>
                </div>
              ))}
            </dl>
            <div className="mb-4 flex flex-wrap gap-2">
              <button disabled={busy} onClick={openFile} className="rounded border px-3 py-1 text-sm">Xem file gốc</button>
              <button disabled={busy || inv.status === "dang_xu_ly"} onClick={runCheck}
                className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50">Kiểm tra sơ bộ</button>
              {["loi_xu_ly", "cho_xac_nhan"].includes(inv.status) && (
                <button disabled={busy} onClick={reprocess} className="rounded border px-3 py-1 text-sm">Xử lý lại</button>
              )}
            </div>
            {inv.status === "loi_xu_ly" && (
              <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">
                Không đọc được hóa đơn (dịch vụ AI tắt hoặc hết hạn mức). Hãy thử “Xử lý lại” sau.
              </p>
            )}
            {check && <CheckResult c={check} />}
          </>
        )}
      </aside>
    </div>
  );
}

function Flag({ ok, label }) {
  const mark = ok === null ? ["?", "text-slate-500"] : ok ? ["✓", "text-green-700"] : ["✗", "text-red-700"];
  return <li className={mark[1]}><b>{mark[0]}</b> {label}</li>;
}

function CheckResult({ c }) {
  return (
    <section className="rounded border p-3 text-sm">
      <h3 className="mb-2 font-medium">Kết quả kiểm tra sơ bộ</h3>
      <ul className="mb-2 space-y-1">
        <Flag ok={c.mst_valid} label="MST người bán đúng định dạng" />
        <Flag ok={c.total_matches} label="Tiền trước thuế + thuế = tổng thanh toán" />
        <Flag ok={!c.duplicate} label="Không trùng hóa đơn đã có" />
      </ul>
      {c.issues.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-amber-800">{c.issues.map((i) => <li key={i}>{i}</li>)}</ul>
      )}
      {c.vendor_suggestion && (
        <p className="mt-2 text-slate-600">Gợi ý tên chuẩn: <b>{c.vendor_suggestion.canonical}</b></p>
      )}
    </section>
  );
}
