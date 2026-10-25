import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client.js";

// ---------------------------------------------------------
// COMPONENT PHÂN TRANG DÙNG CHUNG
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
          <option value={100}>100</option>
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


// B7: danh muc tai khoan (TT133) va loai khoan kem cach viet khac. Moi nguoi xem duoc; chi ke toan truong (KTT) sua.
function useRole() {
  const [role, setRole] = useState(null);
  useEffect(() => { api("/api/auth/me").then((u) => setRole(u.role_name)).catch(() => setRole("")); }, []);
  return role;
}

function Accounts({ canEdit }) {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [form, setForm] = useState({ account_code: "", account_name: "" });
  const [editing, setEditing] = useState(null);   // {code, name}
  const [err, setErr] = useState("");
  
  // THÊM MỚI: State phân trang
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10); // Danh mục tài khoản thì để mặc định 10 cho gọn màn hình
  
  const load = useCallback(() => api(`/api/accounts?q=${encodeURIComponent(q)}`).then((r) => {
    setRows(r.data);
    setCurrentPage(1); // Gõ search xong reset về trang 1
  }).catch((e) => setErr(e.message)), [q]);
  
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  const act = (fn) => async () => { setErr(""); try { await fn(); await load(); } catch (e) { setErr(e.message); } };
  const add = act(async () => {
    await api("/api/accounts", { method: "POST", body: form });
    setForm({ account_code: "", account_name: "" });
  });
  const rename = act(async () => {
    await api(`/api/accounts/${editing.code}`, { method: "PUT", body: { account_name: editing.name } });
    setEditing(null);
  });
  const remove = (a) => act(async () => {
    if (window.confirm(`Xóa tài khoản ${a.account_code} – ${a.account_name}?`)) await api(`/api/accounts/${a.account_code}`, { method: "DELETE" });
  })();

  // Cắt mảng hiển thị theo trang
  const currentRows = rows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm mã hoặc tên tài khoản" aria-label="Tìm tài khoản"
          className="w-72 rounded border p-2 text-sm" />
      </div>
      {err && <p role="alert" className="mb-2 rounded bg-red-50 p-2 text-sm text-red-700">{err}</p>}
      {canEdit && (
        <form className="mb-3 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); add(); }}>
          <input value={form.account_code} onChange={(e) => setForm({ ...form, account_code: e.target.value })}
            placeholder="Mã (3–10 số)" aria-label="Mã tài khoản mới" className="w-36 rounded border p-2 text-sm" required />
          <input value={form.account_name} onChange={(e) => setForm({ ...form, account_name: e.target.value })}
            placeholder="Tên tài khoản" aria-label="Tên tài khoản mới" className="w-72 rounded border p-2 text-sm" required />
          <button className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-blue-700">+ Thêm tài khoản</button>
        </form>
      )}
      
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow flex flex-col">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase text-slate-600">
            <tr><th className="w-32 px-6 py-3 font-semibold">Mã</th><th className="px-6 py-3 font-semibold">Tên tài khoản</th>{canEdit && <th className="w-40 px-3 py-2" />}</tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {currentRows.map((a) => ( // SỬA: Map theo currentRows thay vì rows
              <tr key={a.account_code} className="border-t">
                <td className="px-5 py-3 font-medium tabular-nums">{a.account_code}</td>
                <td className="px-5 py-3">
                  {editing?.code === a.account_code ? (
                    <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); rename(); }}>
                      <input autoFocus value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                        aria-label="Tên mới" className="w-full rounded border p-1 text-sm" />
                      <button className="text-blue-700">Lưu</button>
                      <button type="button" onClick={() => setEditing(null)}>Hủy</button>
                    </form>
                  ) : a.account_name}
                </td>
                {canEdit && (
                  <td className="space-x-3 px-5 py-3 text-right">
                    <button className="text-blue-700" onClick={() => setEditing({ code: a.account_code, name: a.account_name })}>Sửa tên</button>
                    <button className="text-red-600" onClick={() => remove(a)}>Xóa</button>
                  </td>
                )}
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={3} className="px-3 py-6 text-center text-slate-500">Không có tài khoản nào.</td></tr>}
          </tbody>
        </table>
        
        {/* TÍCH HỢP PHÂN TRANG VÀO ĐÂY */}
        {rows.length > 0 && (
          <Pagination 
            totalItems={rows.length}
            pageSize={pageSize}
            currentPage={currentPage}
            setPageSize={setPageSize}
            setCurrentPage={setCurrentPage}
          />
        )}
      </div>
    </div>
  );
}

function Categories({ canEdit }) {
  const [cats, setCats] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [form, setForm] = useState({ category_name: "", default_debit_account: "" });
  const [aliasDraft, setAliasDraft] = useState({});
  const [err, setErr] = useState("");
  
  // THÊM MỚI: Phân trang cho Loại khoản
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  
  const load = useCallback(() => Promise.all([api("/api/categories"), api("/api/accounts")])
    .then(([c, a]) => { setCats(c.data); setAccounts(a.data); }).catch((e) => setErr(e.message)), []);
  useEffect(() => { load(); }, [load]);

  const act = (fn) => async () => { setErr(""); try { await fn(); await load(); } catch (e) { setErr(e.message); } };
  const body = (c) => ({ category_name: c.category_name, default_debit_account: c.default_debit_account || null });

  // Cắt mảng hiển thị theo trang
  const currentCats = cats.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div>
      <p className="mb-3 text-sm text-slate-600">
        Loại khoản gom các “cách viết khác” thường gặp trong tên người bán. Khi tên người bán chứa một cách viết (không phân biệt dấu, hoa/thường),
        hệ thống gợi ý Nợ theo tài khoản mặc định của loại khoản đó, trước cả mô hình ML.
      </p>
      {err && <p role="alert" className="mb-2 rounded bg-red-50 p-2 text-sm text-red-700">{err}</p>}
      {canEdit && (
        <form className="mb-3 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); act(async () => {
          await api("/api/categories", { method: "POST", body: { ...form, default_debit_account: form.default_debit_account || null } });
          setForm({ category_name: "", default_debit_account: "" });
        })(); }}>
          <input value={form.category_name} onChange={(e) => setForm({ ...form, category_name: e.target.value })}
            placeholder="Tên loại khoản mới" aria-label="Tên loại khoản mới" className="w-64 rounded border p-2 text-sm" required />
          <select value={form.default_debit_account} onChange={(e) => setForm({ ...form, default_debit_account: e.target.value })}
            aria-label="Tài khoản Nợ mặc định" className="w-64 rounded border p-2 text-sm">
            <option value="">Tài khoản Nợ mặc định (tùy chọn)</option>
            {accounts.map((a) => <option key={a.account_code} value={a.account_code}>{a.account_code} – {a.account_name}</option>)}
          </select>
          <button className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-blue-700">+ Thêm loại khoản</button>
        </form>
      )}
      
      <div className="flex flex-col rounded-lg border border-slate-200 shadow bg-white overflow-hidden">
        <ul className="space-y-0 divide-y divide-slate-200">
          {currentCats.map((c) => ( // SỬA: Dùng currentCats
            <li key={c.category_id} className="p-4 bg-white hover:bg-slate-50 transition-colors">
              <div className="flex flex-wrap items-center gap-2">
                <b>{c.category_name}</b>
                <span className="text-sm text-slate-500">Nợ mặc định:</span>
                {canEdit ? (
                  <select value={c.default_debit_account || ""} aria-label={`Nợ mặc định của ${c.category_name}`}
                    onChange={(e) => act(() => api(`/api/categories/${c.category_id}`, { method: "PUT",
                      body: { ...body(c), default_debit_account: e.target.value || null } }))()}
                    className="rounded border p-1 text-sm">
                    <option value="">(chưa đặt – không dùng để gợi ý)</option>
                    {accounts.map((a) => <option key={a.account_code} value={a.account_code}>{a.account_code} – {a.account_name}</option>)}
                  </select>
                ) : <span className="text-sm">{c.default_debit_account || "(chưa đặt)"}</span>}
                {canEdit && <button className="ml-auto text-red-600" onClick={act(async () => {
                  if (window.confirm(`Xóa loại khoản “${c.category_name}” và các cách viết khác của nó?`)) await api(`/api/categories/${c.category_id}`, { method: "DELETE" });
                })}>Xóa loại khoản</button>}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {c.aliases.map((a) => (
                  <span key={a.alias_id} className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-sm">
                    {a.alias_text}
                    {canEdit && <button aria-label={`Xóa cách viết ${a.alias_text}`} className="text-red-600"
                      onClick={act(() => api(`/api/categories/${c.category_id}/aliases/${a.alias_id}`, { method: "DELETE" }))}>×</button>}
                  </span>
                ))}
                {c.aliases.length === 0 && <span className="text-sm text-slate-500">Chưa có cách viết khác nào.</span>}
                {canEdit && (
                  <form className="flex gap-1" onSubmit={(e) => { e.preventDefault(); act(async () => {
                    await api(`/api/categories/${c.category_id}/aliases`, { method: "POST", body: { alias_text: aliasDraft[c.category_id] || "" } });
                    setAliasDraft((d) => ({ ...d, [c.category_id]: "" }));
                  })(); }}>
                    <input value={aliasDraft[c.category_id] || ""} aria-label={`Thêm cách viết khác cho ${c.category_name}`} placeholder="+ cách viết khác"
                      onChange={(e) => setAliasDraft((d) => ({ ...d, [c.category_id]: e.target.value }))}
                      className="w-40 rounded border p-1 text-sm" />
                    <button className="text-sm text-blue-700">Thêm</button>
                  </form>
                )}
              </div>
            </li>
          ))}
          {cats.length === 0 && <li className="p-6 text-center text-sm text-slate-500">Chưa có loại khoản nào.</li>}
        </ul>
        
        {/* TÍCH HỢP PHÂN TRANG VÀO ĐÂY */}
        {cats.length > 0 && (
          <Pagination 
            totalItems={cats.length}
            pageSize={pageSize}
            currentPage={currentPage}
            setPageSize={setPageSize}
            setCurrentPage={setCurrentPage}
          />
        )}
      </div>
    </div>
  );
}

export default function Catalog() {
  const role = useRole();
  const [tab, setTab] = useState("accounts");
  const canEdit = role === "KTT";
  return (
    <section className="mx-auto max-w-6xl">
      <h2 className="mb-2 text-2xl font-bold text-slate-800">Danh mục</h2>
      {role !== null && !canEdit && (
        <p className="mb-3 text-sm text-slate-600">Bạn chỉ xem được. Chỉ kế toán trưởng thêm, sửa, xóa được danh mục.</p>
      )}
      <div className="mb-6 flex gap-3 text-sm" role="tablist">
        {[["accounts", "Tài khoản (TT133)"], ["categories", "Loại khoản"]].map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`rounded-full px-5 py-2 ${tab === k ? "bg-blue-600 font-semibold text-white shadow-sm" : "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"}`}>
            {label}
          </button>
        ))}
      </div>
      {tab === "accounts" ? <Accounts canEdit={canEdit} /> : <Categories canEdit={canEdit} />}
    </section>
  );
}