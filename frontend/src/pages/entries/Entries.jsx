import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../../api/client.js";
import StatusBadge from "../invoices/StatusBadge.jsx";
import { money } from "../invoices/format.js";
import InvoicePicker from "../review/InvoicePicker.jsx";

// B7: man hinh dinh khoan. Hien goi y No/Co (kem nguon goi y), cho sua tung dong, roi luu.
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

function AccountSelect({ value, onChange, accounts, label, disabled }) {
  const known = accounts.some((a) => a.account_code === value);
  return (
    <select aria-label={label} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}
      className="w-full rounded border p-1.5 text-sm disabled:opacity-70">
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
  const [err, setErr] = useState("");
  const [warnings, setWarnings] = useState([]);
  const [msg, setMsg] = useState("");
  const run = useRef(0);                         // bo qua ket qua tra ve muon khi da doi hoa don

  async function suggest(token = run.current) {
    setBusy("suggest"); setErr(""); setMsg("");
    try {
      const r = await api(`/api/invoices/${id}/suggest-entries`, { method: "POST" });
      if (token !== run.current) return;
      setRows(r.data.map((e) => newRow({ ...e, probability: e.probability ?? null })));
      setWarnings(r.warnings || []); setDirty(true); setSaved(false);
    } catch (e) { if (token === run.current) setErr(e.message); }
    finally { if (token === run.current) setBusy(""); }
  }

  useEffect(() => {
    if (!id) return;
    const token = ++run.current;
    setInv(null); setRows([]); setErr(""); setMsg(""); setWarnings([]); setDirty(false); setSaved(false); setBusy("load");
    Promise.all([api(`/api/invoices/${id}`), api(`/api/invoices/${id}/journal-entries`), api("/api/accounts")])
      .then(([i, j, a]) => {
        if (token !== run.current) return;
        setInv(i.data); setAccounts(a.data); setEditable(j.editable);
        if (j.data.length) {
          setRows(j.data.map((e) => newRow({ ...e, source: "saved" }))); setSaved(true); setBusy("");
        } else if (j.editable) { setBusy(""); suggest(token); }
        else setBusy("");
      })
      .catch((e) => { if (token === run.current) { setErr(e.message); setBusy(""); } });
  }, [id]);

  const errors = rows.map(rowError);
  const total = rows.reduce((s, r) => s + (AMOUNT_RE.test(r.amount) ? cents(r.amount) : 0), 0);
  const invTotal = inv?.total_amount != null ? Math.round(Number(inv.total_amount) * 100) : null;
  const diff = invTotal == null ? null : total - invTotal;
  const canSave = editable && rows.length > 0 && errors.every((x) => !x) && busy === "";

  const patch = (key, p) => { setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...p, edited: true } : r))); setDirty(true); setSaved(false); setMsg(""); };

  async function save() {
    setBusy("save"); setErr(""); setMsg("");
    try {
      const r = await api(`/api/invoices/${id}/journal-entries`, { method: "PUT",
        body: { entries: rows.map(({ debit_account, credit_account, amount }) => ({ debit_account, credit_account, amount })) } });
      setRows(r.data.map((e) => newRow({ ...e, source: "saved" })));
      setWarnings(r.warnings || []); setDirty(false); setSaved(true); setMsg("Đã lưu bút toán.");
    } catch (e) { setErr(e.message); } finally { setBusy(""); }
  }

  async function submit() {
    if (!window.confirm("Gửi hóa đơn này cho kế toán trưởng duyệt? Sau khi gửi sẽ không sửa được trường và bút toán.")) return;
    setBusy("submit"); setErr("");
    try {
      await api(`/api/invoices/${id}/submit`, { method: "POST" });
      const i = await api(`/api/invoices/${id}`);
      setInv(i.data); setEditable(false); setMsg("Đã gửi kế toán trưởng duyệt.");
    } catch (e) { setErr(e.message); } finally { setBusy(""); }
  }

  const sorted = useMemo(() => [...accounts].sort((a, b) => a.account_code.localeCompare(b.account_code)), [accounts]);

  if (!id) return <InvoicePicker title="Bút toán gợi ý"
    hint="Chọn một hóa đơn để xem gợi ý định khoản Nợ/Có, chỉnh lại nếu cần và lưu." />;
  if (!inv) return (
    <p className={`text-sm ${err ? "text-red-600" : "text-slate-500"}`}>
      {err || "Đang tải…"} {err && <button className="text-blue-700" onClick={() => setParams({})}>← Danh sách</button>}
    </p>
  );

  return (
    <section className="max-w-5xl">
      <div className="mb-3 flex flex-wrap items-center gap-3 text-sm">
        <button className="text-blue-700" onClick={() => setParams({})}>← Danh sách</button>
        <h1 className="text-lg font-semibold">Định khoản hóa đơn #{inv.invoice_id}</h1>
        <StatusBadge status={inv.status} />
        <Link to={`/review?id=${inv.invoice_id}`} className="ml-auto text-blue-700">← Kiểm tra trường</Link>
      </div>
      <dl className="mb-3 grid grid-cols-2 gap-x-6 gap-y-1 rounded border bg-white p-3 text-sm md:grid-cols-4">
        <div><dt className="text-slate-500">Người bán</dt><dd className="truncate" title={inv.seller_name}>{inv.seller_name || "—"}</dd></div>
        <div><dt className="text-slate-500">Tiền trước thuế</dt><dd className="tabular-nums">{money(inv.total_before_tax)}</dd></div>
        <div><dt className="text-slate-500">Thuế GTGT ({inv.vat_rate ?? "—"}%)</dt><dd className="tabular-nums">{money(inv.vat_amount)}</dd></div>
        <div><dt className="text-slate-500">Tổng thanh toán</dt><dd className="font-medium tabular-nums">{money(inv.total_amount)}</dd></div>
      </dl>
      {!editable && (
        <p className="mb-3 rounded bg-amber-50 p-2 text-sm text-amber-800">
          Hóa đơn đang ở trạng thái “{inv.status}” nên chỉ xem bút toán đã lưu, không sửa được.
        </p>
      )}
      {err && <p role="alert" className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{err}</p>}
      {warnings.map((w) => <p key={w} className="mb-2 rounded bg-amber-50 p-2 text-sm text-amber-800">⚠ {w}</p>)}
      {busy === "suggest" && <p className="mb-3 text-sm text-slate-500">Đang gợi ý định khoản… (người bán mới có thể mất vài giây nếu phải hỏi Gemini)</p>}

      <div className="overflow-x-auto rounded border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase text-slate-600">
            <tr>{["Tài khoản Nợ", "Tài khoản Có", "Số tiền (VND)", "Nguồn gợi ý", ""].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const [label, cls] = SOURCE[r.source] || SOURCE.manual;
              return (
                <tr key={r.key} className="border-t align-top">
                  <td className="min-w-[14rem] px-3 py-2"><AccountSelect label={`Dòng ${i + 1}: tài khoản Nợ`} value={r.debit_account} accounts={sorted} disabled={!editable}
                    onChange={(v) => patch(r.key, { debit_account: v })} /></td>
                  <td className="min-w-[14rem] px-3 py-2"><AccountSelect label={`Dòng ${i + 1}: tài khoản Có`} value={r.credit_account} accounts={sorted} disabled={!editable}
                    onChange={(v) => patch(r.key, { credit_account: v })} /></td>
                  <td className="px-3 py-2">
                    <input aria-label={`Dòng ${i + 1}: số tiền`} inputMode="decimal" value={r.amount} disabled={!editable}
                      onChange={(e) => patch(r.key, { amount: e.target.value.replace(/[^\d.]/g, "") })}
                      className="w-36 rounded border p-1.5 text-right tabular-nums disabled:opacity-70" />
                    {errors[i] && editable && <p role="alert" className="mt-1 max-w-[9rem] text-xs text-red-600">{errors[i]}</p>}
                  </td>
                  <td className="max-w-[18rem] px-3 py-2">
                    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${cls}`}>{label}</span>
                    {r.probability != null && <span className="ml-1 text-xs text-slate-500">chắc {Math.round(r.probability * 100)}%</span>}
                    {r.edited && r.source !== "saved" && r.source !== "manual" && <span className="ml-1 text-xs text-blue-700">đã sửa</span>}
                    {r.note && <p className="mt-1 text-xs text-slate-500">{r.note}</p>}
                  </td>
                  <td className="px-3 py-2">
                    {editable && <button className="text-red-600" aria-label={`Xóa dòng ${i + 1}`}
                      onClick={() => { setRows((rs) => rs.filter((x) => x.key !== r.key)); setDirty(true); setSaved(false); }}>Xóa</button>}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && busy === "" && (
              <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-500">Chưa có bút toán.</td></tr>
            )}
          </tbody>
          <tfoot>
            <tr className="border-t bg-slate-50">
              <td colSpan={2} className="px-3 py-2 text-right text-slate-600">Tổng các dòng</td>
              <td className="px-3 py-2 text-right font-medium tabular-nums">{money(total / 100)}</td>
              <td colSpan={2} className={`px-3 py-2 text-xs ${diff === 0 ? "text-green-700" : "text-amber-700"}`}>
                {diff == null ? "" : diff === 0 ? "✓ Khớp tổng thanh toán" : `Lệch ${money(Math.abs(diff) / 100)} so với tổng thanh toán`}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        {editable && <>
          <button disabled={busy !== ""} onClick={() => { setRows((rs) => [...rs, newRow()]); setDirty(true); setSaved(false); }}
            className="rounded border px-3 py-1 disabled:opacity-50">+ Thêm dòng</button>
          <button disabled={busy !== ""} onClick={() => {
            if (!dirty || window.confirm("Gợi ý lại sẽ thay các dòng đang sửa. Tiếp tục?")) suggest();
          }} className="rounded border px-3 py-1 disabled:opacity-50">Gợi ý lại</button>
          <button disabled={!canSave} onClick={save} className="rounded bg-blue-600 px-4 py-1 text-white disabled:opacity-50">
            {busy === "save" ? "Đang lưu…" : "Lưu bút toán"}
          </button>
        </>}
        {editable && saved && !dirty && (
          <button disabled={busy !== ""} onClick={submit} className="rounded bg-green-600 px-4 py-1 text-white disabled:opacity-50">
            Gửi kế toán trưởng duyệt
          </button>
        )}
        {dirty && editable && <span className="text-amber-700">Có thay đổi chưa lưu</span>}
        {msg && <span role="status" className="text-green-700">{msg}</span>}
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Gợi ý lấy theo thứ tự: lịch sử định khoản của người bán → loại khoản khớp tên người bán → mô hình ML → Gemini (người bán mới, mô hình chưa chắc) → mặc định.
        Thuế GTGT đầu vào mặc định coi là đủ điều kiện khấu trừ (Nợ 1331). Đây là gợi ý, kế toán chịu trách nhiệm kiểm tra.
      </p>
    </section>
  );
}
