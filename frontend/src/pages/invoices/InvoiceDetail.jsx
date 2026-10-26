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

const POLL_MS = 1000;
const POLL_LIMIT_MS = 10 * 60 * 1000;   // khop voi thoi gian cho toi da cua backend (hoa don xep hang cuoi co the cho lau)
const SUCCESS_SHOW_MS = 8000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export default function InvoiceDetail({ invoiceId, onClose, onChanged }) {
  const [inv, setInv] = useState(null);
  const [check, setCheck] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [prog, setProg] = useState(null);   // {percent, stage} khi dang doc/xu ly lai
  const [done, setDone] = useState("");     // thong bao thanh cong, tu mat sau vai giay

  const load = () => api(`/api/invoices/${invoiceId}`).then((r) => { setInv(r.data); setCheck(r.data.checks); })
    .catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [invoiceId]);

  // Hoa don dang xu ly (vua tai len hoac bam "Xu ly lai"): hoi tien do moi giay cho den khi xong, nhu luc tai len.
  const processing = inv?.status === "dang_xu_ly";
  useEffect(() => {
    if (!processing) return;
    let stop = false;
    (async () => {
      const t0 = Date.now();
      let fails = 0;
      setDone("");
      while (!stop && Date.now() - t0 < POLL_LIMIT_MS) {
        try {
          const { data } = await api(`/api/invoices/${invoiceId}/progress`);
          if (stop) return;
          fails = 0;
          if (data.status !== "dang_xu_ly") {
            setProg(null);
            if (data.status !== "loi_xu_ly") setDone("Đọc dữ liệu thành công");
            await load();
            onChanged?.();
            return;
          }
          setProg({ percent: data.percent, stage: data.stage });
        } catch {
          if (++fails >= 5) break;
        }
        await sleep(POLL_MS);
      }
      if (!stop) { setProg(null); load(); }   // het gio cho: tai lai de thay trang thai that
    })();
    return () => { stop = true; };
  }, [processing, invoiceId]);

  useEffect(() => {
    if (!done) return;
    const t = setTimeout(() => setDone(""), SUCCESS_SHOW_MS);
    return () => clearTimeout(t);
  }, [done]);

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
            {processing && (
              <div className="mb-3 rounded border bg-white p-3 text-sm" aria-live="polite">
                <div className="flex items-center gap-2">
                  <span className="truncate">{prog?.stage || "Đang chờ xử lý"}</span>
                  <span className="ml-auto shrink-0 text-slate-500">{prog?.percent ?? 5}%</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-200" role="progressbar"
                  aria-valuemin={0} aria-valuemax={100} aria-valuenow={prog?.percent ?? 5} aria-label="Tiến độ xử lý hóa đơn">
                  <div className="h-full rounded-full bg-blue-600 transition-all duration-500" style={{ width: `${prog?.percent ?? 5}%` }} />
                </div>
              </div>
            )}
            {done && <p className="mb-3 rounded bg-green-50 p-2 text-sm text-green-700">✓ {done}</p>}
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

// Moi kiem tra co 3 trang thai, moi trang thai co cau chu rieng (khong dung chung mot cau cho ca dung lan sai):
// ok -> xanh + dau ✓ ; loi -> do + dau ✗ + noi ro "khong/khac" ; chua ro (thieu so lieu) -> xam + dau ?
const TONE = {
  ok: { mark: "✓", row: "text-green-700", tag: "Đạt", tagCls: "bg-green-100 text-green-800" },
  bad: { mark: "✗", row: "text-red-700", tag: "Không đạt", tagCls: "bg-red-100 text-red-800" },
  unknown: { mark: "?", row: "text-slate-500", tag: "Chưa kiểm tra được", tagCls: "bg-slate-200 text-slate-700" },
};

function Check({ state, label, details = [] }) {
  const t = TONE[state];
  return (
    <li className={t.row}>
      <div className="flex items-start gap-2">
        <b className="w-4 shrink-0 text-center">{t.mark}</b>
        <span className="flex-1">{label}</span>
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${t.tagCls}`}>{t.tag}</span>
      </div>
      {details.map((d) => <p key={d} className="ml-6 mt-0.5 text-xs">{d}</p>)}
    </li>
  );
}

function CheckResult({ c }) {
  const d = c.issue_details || { mst: [], totals: c.issues || [], duplicate: [] };
  const mst = c.mst_valid ? "ok" : "bad";
  const totals = c.total_matches === null ? "unknown" : c.total_matches ? "ok" : "bad";
  const dup = c.duplicate ? "bad" : "ok";
  const bad = [mst, totals, dup].filter((x) => x === "bad").length;
  const unknown = [mst, totals, dup].filter((x) => x === "unknown").length;
  return (
    <section className="rounded border p-3 text-sm">
      <h3 className="mb-1 font-medium">Kết quả kiểm tra sơ bộ</h3>
      <p className={`mb-2 text-xs font-medium ${bad ? "text-red-700" : unknown ? "text-slate-500" : "text-green-700"}`}>
        {bad ? `Có ${bad} mục không đạt, cần xem lại trước khi xác nhận`
          : unknown ? "Chưa có lỗi, nhưng còn mục chưa kiểm tra được" : "Tất cả mục kiểm tra đều đạt"}
      </p>
      <ul className="space-y-2">
        <Check state={mst}
          label={mst === "ok" ? "MST người bán đúng định dạng" : "MST người bán không đúng định dạng"} details={d.mst} />
        <Check state={totals}
          label={totals === "ok" ? "Tổng tiền khớp: tiền trước thuế + thuế = tổng thanh toán"
            : totals === "bad" ? "Tổng tiền không khớp" : "Chưa kiểm tra được tổng tiền"}
          details={d.totals} />
        <Check state={dup}
          label={dup === "ok" ? "Không trùng hóa đơn đã có" : "Trùng với hóa đơn đã có"} details={d.duplicate} />
      </ul>
      {c.vendor_suggestion && (
        <p className="mt-3 text-slate-600">Gợi ý tên chuẩn: <b>{c.vendor_suggestion.canonical}</b></p>
      )}
    </section>
  );
}
