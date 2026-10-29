import { useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { api } from "../../api/client.js";
import StatusBadge from "../invoices/StatusBadge.jsx";
import { money } from "../invoices/format.js";

// B7: man hinh dinh khoan. Hien goi y No/Co (kem nguon goi y), cho sua tung dong, roi luu.
// Mo tu man hinh Kiem tra (nut "Tiep: Dinh khoan"). Goi y AI co the cham: trong luc cho van nhap tay duoc,
// goi y den sau khong ghi de phan da nhap, va ban nhap duoc nho de quay lai khong phai hoi AI lai.
const SOURCE = {
  history: ["Lịch sử người bán", "bg-green-100 text-green-800"],
  alias: ["Loại khoản", "bg-green-100 text-green-800"],
  ml: ["Mô hình ML", "bg-blue-100 text-blue-800"],
  llm: ["Gemini", "bg-violet-100 text-violet-800"],
  rule: ["Mặc định", "bg-slate-200 text-slate-700"],
  saved: ["Đã lưu", "bg-slate-100 text-slate-700"],
  manual: ["Nhập tay", "bg-slate-100 text-slate-700"],
};
const AMOUNT_RE = /^\d{1,16}(\.\d{1,2})?$/;
const AI_TIMEOUT_S = 40;                       // qua ngung nay thi thoi cho, de ke toan nhap tay
let seq = 0;
const newRow = (o = {}) => ({ key: ++seq, debit_account: "", credit_account: "", amount: "", source: "manual",
  probability: null, note: "", edited: false, ...o });
const cents = (s) => Math.round(parseFloat(s) * 100);

function rowError(r) {
  if (!r.debit_account || !r.credit_account) return "Chọn đủ tài khoản Nợ và Có";
  if (r.debit_account === r.credit_account) return "Nợ và Có không được trùng nhau";
  if (!AMOUNT_RE.test(r.amount) || cents(r.amount) <= 0) return "Số tiền > 0, tối đa 2 chữ số thập phân";
  return "";
}

const draftKey = (id) => `entries.draft.${id}`;
function loadDraft(id) {
  try { const d = JSON.parse(sessionStorage.getItem(draftKey(id)) || "null"); return Array.isArray(d) && d.length ? d : null; }
  catch { return null; }
}
function saveDraft(id, rows) {
  try {
    if (rows) sessionStorage.setItem(draftKey(id), JSON.stringify(rows.map(({ key, ...r }) => r)));
    else sessionStorage.removeItem(draftKey(id));
  } catch { /* trinh duyet chan sessionStorage: bo qua, chi mat ban nhap */ }
}

function AccountSelect({ value, onChange, accounts, label, disabled }) {
  const known = accounts.some((a) => a.account_code === value);
  return (
    <select aria-label={label} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}
      className="w-full rounded border border-slate-300 bg-white p-2 text-sm disabled:opacity-70">
      <option value="">— chọn —</option>
      {!known && value && <option value={value}>{value} (không còn trong danh mục)</option>}
      {accounts.map((a) => <option key={a.account_code} value={a.account_code}>{a.account_code} – {a.account_name}</option>)}
    </select>
  );
}

export default function Entries() {
  const [params, setParams] = useSearchParams();
  const id = params.get("id");
  const [inv, setInv] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [rows, setRows] = useState([]);
  const [editable, setEditable] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState("");          // "" | "load" | "suggest" | "save" | "submit"
  const [wait, setWait] = useState(0);           // so giay da cho AI
  const [pending, setPending] = useState(null);  // goi y den muon khi ke toan da nhap tay
  const [err, setErr] = useState("");
  const [warnings, setWarnings] = useState([]);
  const [msg, setMsg] = useState("");
  const run = useRef(0);                         // bo qua ket qua tra ve muon khi da doi hoa don
  const sug = useRef(0);                         // so thu tu lan goi y hien hanh
  const rowsRef = useRef([]);
  rowsRef.current = rows;

  const toRows = (list, extra = {}) => list.map((e) => newRow({ ...e, probability: e.probability ?? null, ...extra }));

  async function suggest({ replace = false } = {}) {
    const token = run.current, me = ++sug.current;
    setBusy("suggest"); setErr(""); setMsg(""); setPending(null); setWait(0);
    const timer = setInterval(() => setWait((w) => w + 1), 1000);
    const stale = () => token !== run.current || me !== sug.current;
    try {
      const r = await Promise.race([
        api(`/api/invoices/${id}/suggest-entries`, { method: "POST" }),
        new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), AI_TIMEOUT_S * 1000)),
      ]);
      if (stale()) return;
      const fresh = toRows(r.data);
      setWarnings(r.warnings || []);
      if (!replace && rowsRef.current.length > 0) setPending(fresh);   // da nhap tay: khong ghi de, hoi truoc
      else { setRows(fresh); setDirty(true); setSaved(false); }
    } catch (e) {
      if (stale()) return;
      setErr(e.message === "timeout"
        ? `AI chưa trả lời sau ${AI_TIMEOUT_S} giây. Bạn có thể nhập bút toán thủ công hoặc bấm “Gợi ý lại”.`
        : e.message);
    } finally {
      clearInterval(timer);
      if (!stale()) setBusy("");
    }
  }

  useEffect(() => {
    if (!id) return;
    const token = ++run.current;
    sug.current++;
    setInv(null); setRows([]); setErr(""); setMsg(""); setWarnings([]); setDirty(false); setSaved(false);
    setPending(null); setBusy("load");
    Promise.all([api(`/api/invoices/${id}`), api(`/api/invoices/${id}/journal-entries`), api("/api/accounts")])
      .then(([i, j, a]) => {
        if (token !== run.current) return;
        setInv(i.data); setAccounts(a.data); setEditable(j.editable);
        const draft = j.editable && !j.data.length ? loadDraft(id) : null;
        if (j.data.length) {
          setRows(toRows(j.data, { source: "saved" })); setSaved(true); setBusy("");
        } else if (draft) {                         // quay lai tu man hinh Kiem tra: dung ban nhap, KHONG hoi AI lai
          setRows(toRows(draft)); setDirty(true); setBusy("");
          setMsg("Đã khôi phục bản nháp của bạn. Bấm “Gợi ý lại” nếu muốn AI gợi ý mới.");
        } else if (j.editable) { setBusy(""); suggest(); }
        else setBusy("");
      })
      .catch((e) => { if (token === run.current) { setErr(e.message); setBusy(""); } });
    return () => { sug.current++; };
  }, [id]);

  // nho ban nhap theo tung hoa don (chi trong tab nay) de quay lai khong mat va khong ton luot AI
  useEffect(() => {
    if (id && editable && dirty && rows.length) saveDraft(id, rows);
  }, [id, editable, dirty, rows]);

  const errors = rows.map(rowError);
  const total = rows.reduce((s, r) => s + (AMOUNT_RE.test(r.amount) ? cents(r.amount) : 0), 0);
  const invTotal = inv?.total_amount != null ? Math.round(Number(inv.total_amount) * 100) : null;
  const diff = invTotal == null ? null : total - invTotal;
  const idle = busy === "" || busy === "suggest";   // dang cho AI van duoc nhap tay va luu
  const canSave = editable && rows.length > 0 && errors.every((x) => !x) && idle;

  const touch = () => { setDirty(true); setSaved(false); setMsg(""); };
  const patch = (key, p) => { setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...p, edited: true } : r))); touch(); };

  async function save() {
    sug.current++;                                  // bo qua goi y AI den muon
    setBusy("save"); setErr(""); setMsg(""); setPending(null);
    try {
      const r = await api(`/api/invoices/${id}/journal-entries`, { method: "PUT",
        body: { entries: rows.map(({ debit_account, credit_account, amount }) => ({ debit_account, credit_account, amount })) } });
      setRows(toRows(r.data, { source: "saved" }));
      setWarnings(r.warnings || []); setDirty(false); setSaved(true); setMsg("Đã lưu bút toán.");
      saveDraft(id, null);
    } catch (e) { setErr(e.message); } finally { setBusy(""); }
  }

  async function submit() {
    if (!window.confirm("Gửi hóa đơn này cho kế toán trưởng duyệt? Sau khi gửi sẽ không sửa được trường và bút toán.")) return;
    setBusy("submit"); setErr("");
    try {
      await api(`/api/invoices/${id}/submit`, { method: "POST" });
      const i = await api(`/api/invoices/${id}`);
      setInv(i.data); setEditable(false); setMsg("Đã gửi kế toán trưởng duyệt."); saveDraft(id, null);
    } catch (e) { setErr(e.message); } finally { setBusy(""); }
  }

  const sorted = useMemo(() => [...accounts].sort((a, b) => a.account_code.localeCompare(b.account_code)), [accounts]);

  // Dinh khoan chi mo tu man hinh Kiem tra (nut "Tiep: Dinh khoan"), nen khong co ?id thi quay ve Kiem tra
  if (!id) return <Navigate to="/review" replace />;
  if (!inv) return (
    <p className={`text-sm ${err ? "text-red-600" : "text-slate-500"}`}>
      {err || "Đang tải…"} {err && <button className="text-blue-700" onClick={() => setParams({})}>← Danh sách</button>}
    </p>
  );

  return (
    <section className="mx-auto max-w-6xl">
      <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
        <Link to="/review" className="text-blue-700 hover:underline">← Danh sách</Link>
        <h2 className="text-2xl font-bold text-slate-800">Định khoản hóa đơn #{inv.invoice_id}</h2>
        <StatusBadge status={inv.status} />
        <Link to={`/review?id=${inv.invoice_id}`} className="ml-auto text-blue-700 hover:underline">← Kiểm tra trường</Link>
      </div>
      <dl className="mb-4 grid grid-cols-2 gap-x-6 gap-y-3 rounded-lg border border-slate-200 bg-white p-5 text-sm shadow md:grid-cols-4">
        <div><dt className="text-slate-500">Người bán</dt><dd className="font-semibold" title={inv.seller_name}>{inv.seller_name || "—"}</dd></div>
        <div><dt className="text-slate-500">Tiền trước thuế</dt><dd className="font-semibold tabular-nums">{money(inv.total_before_tax)}</dd></div>
        <div><dt className="text-slate-500">Thuế GTGT ({inv.vat_rate ?? "—"}%)</dt><dd className="font-semibold tabular-nums">{money(inv.vat_amount)}</dd></div>
        <div><dt className="text-slate-500">Tổng thanh toán</dt><dd className="font-bold tabular-nums text-blue-700">{money(inv.total_amount)}</dd></div>
      </dl>

      {!editable && (
        <p className="mb-3 rounded bg-amber-50 p-3 text-sm text-amber-800">
          Hóa đơn đang ở trạng thái “{inv.status}” nên chỉ xem bút toán đã lưu, không sửa được.
        </p>
      )}
      {err && <p role="alert" className="mb-3 rounded bg-red-50 p-3 text-sm text-red-700">{err}</p>}
      {warnings.map((w) => <p key={w} className="mb-2 rounded bg-amber-50 p-3 text-sm text-amber-800">⚠ {w}</p>)}

      {busy === "suggest" && (
        <div role="status" className="mb-3 rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
          <div className="flex items-center justify-between gap-3">
            <span>AI đang gợi ý định khoản… <b>{wait}s</b> / tối đa {AI_TIMEOUT_S}s. Chưa đến lượt thì bạn cứ nhập tay: gợi ý đến sau sẽ <b>không ghi đè</b> phần bạn đã nhập.</span>
            <button className="shrink-0 text-blue-700 underline" onClick={() => { sug.current++; setBusy(""); setErr("Đã bỏ chờ AI. Bạn có thể nhập thủ công hoặc bấm “Gợi ý lại”."); }}>Bỏ chờ</button>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded bg-blue-100">
            <div className="h-full bg-blue-500 transition-all" style={{ width: `${Math.min(100, (wait / AI_TIMEOUT_S) * 100)}%` }} />
          </div>
        </div>
      )}
      {pending && (
        <div role="status" className="mb-3 flex flex-wrap items-center gap-3 rounded border border-violet-200 bg-violet-50 p-3 text-sm text-violet-900">
          <span>AI đã có gợi ý ({pending.length} dòng). Bạn đã nhập tay nên chưa thay thế.</span>
          <button className="rounded bg-violet-600 px-3 py-1 text-white" onClick={() => { setRows(pending); setPending(null); touch(); }}>Dùng gợi ý của AI</button>
          <button className="text-violet-700 underline" onClick={() => setPending(null)}>Giữ bút toán của tôi</button>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow">
        <table className="min-w-[56rem] divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-100">
            <tr>{["Tài khoản Nợ", "Tài khoản Có", "Số tiền (VND)", "Nguồn gợi ý", ""].map((h) => (
              <th key={h} className="px-6 py-3 text-xs font-semibold uppercase text-slate-600">{h}</th>))}</tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {rows.map((r, i) => {
              const [label, cls] = SOURCE[r.source] || SOURCE.manual;
              return (
                <tr key={r.key} className="align-top">
                  <td className="min-w-[16rem] px-6 py-4"><AccountSelect label={`Dòng ${i + 1}: tài khoản Nợ`} value={r.debit_account} accounts={sorted} disabled={!editable}
                    onChange={(v) => patch(r.key, { debit_account: v })} /></td>
                  <td className="min-w-[16rem] px-6 py-4"><AccountSelect label={`Dòng ${i + 1}: tài khoản Có`} value={r.credit_account} accounts={sorted} disabled={!editable}
                    onChange={(v) => patch(r.key, { credit_account: v })} /></td>
                  <td className="px-6 py-4">
                    <input aria-label={`Dòng ${i + 1}: số tiền`} inputMode="decimal" value={r.amount} disabled={!editable}
                      onChange={(e) => patch(r.key, { amount: e.target.value.replace(/[^\d.]/g, "") })}
                      className="w-40 rounded border border-slate-300 bg-white p-2 text-right tabular-nums disabled:opacity-70" />
                    {errors[i] && editable && <p role="alert" className="mt-1 max-w-[10rem] text-xs text-red-600">{errors[i]}</p>}
                  </td>
                  <td className="min-w-[14rem] max-w-[22rem] px-6 py-4">
                    <span className={`rounded px-2 py-0.5 text-xs font-semibold ${cls}`}>{label}</span>
                    {r.probability != null && <span className="ml-1 text-xs text-slate-500">chắc {Math.round(r.probability * 100)}%</span>}
                    {r.edited && r.source !== "saved" && r.source !== "manual" && <span className="ml-1 text-xs text-blue-700">đã sửa</span>}
                    {r.note && <p className="mt-1 text-xs text-slate-500">{r.note}</p>}
                  </td>
                  <td className="px-6 py-4">
                    {editable && <button className="text-red-600" aria-label={`Xóa dòng ${i + 1}`}
                      onClick={() => { setRows((rs) => rs.filter((x) => x.key !== r.key)); touch(); }}>Xóa</button>}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && busy !== "load" && (
              <tr><td colSpan={5} className="px-6 py-10 text-center text-slate-500">
                {busy === "suggest" ? "Đang chờ AI… bạn có thể bấm “+ Thêm dòng” để nhập tay." : "Chưa có bút toán. Bấm “+ Thêm dòng” hoặc “Gợi ý lại”."}
              </td></tr>
            )}
          </tbody>
          <tfoot>
            <tr className="border-t bg-slate-50">
              <td colSpan={2} className="px-6 py-4 text-right text-slate-600">Tổng các dòng</td>
              <td className="px-6 py-4 text-right font-bold tabular-nums">{money(total / 100)}</td>
              <td colSpan={2} className={`px-6 py-4 text-xs font-medium ${diff === 0 ? "text-green-700" : "text-amber-700"}`}>
                {diff == null ? "" : diff === 0 ? "✓ Khớp tổng thanh toán" : `Lệch ${money(Math.abs(diff) / 100)} so với tổng thanh toán`}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
        {editable && <>
          <button disabled={!idle} onClick={() => { setRows((rs) => [...rs, newRow()]); touch(); }}
            className="rounded border bg-white px-4 py-2 font-medium shadow-sm hover:bg-slate-50 disabled:opacity-50">+ Thêm dòng</button>
          <button disabled={busy !== "" } onClick={() => {
            if (!dirty || window.confirm("Gợi ý lại sẽ thay các dòng đang sửa. Tiếp tục?")) suggest({ replace: true });
          }} className="rounded border bg-white px-4 py-2 font-medium shadow-sm hover:bg-slate-50 disabled:opacity-50">Gợi ý lại</button>
          <button disabled={!canSave} onClick={save} className="rounded bg-blue-600 px-5 py-2 font-semibold text-white shadow-md hover:bg-blue-700 disabled:opacity-50">
            {busy === "save" ? "Đang lưu…" : "Lưu bút toán"}
          </button>
        </>}
        {editable && saved && !dirty && (
          <button disabled={busy !== ""} onClick={submit} className="rounded bg-green-600 px-5 py-2 font-semibold text-white shadow-md hover:bg-green-700 disabled:opacity-50">
            Gửi kế toán trưởng duyệt
          </button>
        )}
        {dirty && editable && <span className="text-amber-700">Có thay đổi chưa lưu (đã nhớ bản nháp trong tab này)</span>}
        {msg && <span role="status" className="text-green-700">{msg}</span>}
      </div>
      <p className="mt-4 text-xs leading-relaxed text-slate-500">
        Gợi ý lấy theo thứ tự: lịch sử định khoản của người bán → loại khoản khớp tên người bán → mô hình ML → Gemini (người bán mới, mô hình chưa chắc) → mặc định.
        Thuế GTGT đầu vào mặc định coi là đủ điều kiện khấu trừ (Nợ 1331). Đây là gợi ý, kế toán chịu trách nhiệm kiểm tra.
      </p>
    </section>
  );
}
