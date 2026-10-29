import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api, getToken, setToken } from "./api/client.js";
import ThemeToggle from "./components/ThemeToggle.jsx";
import Login from "./pages/Login.jsx";
import { UserContext } from "./userContext.js";
import { Approvals, Entries, Export, PurchaseOrders, Review, Upload } from "./pages/pages.jsx";

// Chu so huu khung giao dien (nav, bao ve route theo vai tro): Duong (C9)
// [duong dan, ten menu, vai tro duoc vao]. KTV = ke toan vien (nhap lieu), KTT = ke toan truong (duyet, xoa).
const NAV = [
  ["/", "Tải hóa đơn", ["KTV"]],
  ["/", "Danh sách hóa đơn", ["KTT"]],
  ["/review", "Kiểm tra", ["KTV"]],
  ["/entries", "Bút toán", ["KTV"]],
  ["/approvals", "Hàng chờ duyệt", ["KTT"]],
  ["/po", "PO", ["KTV"]],
  ["/export", "Xuất", ["KTV", "KTT"]],
];

// Muc dang mo: nen xanh nhat + chu dam + vien; muc khac chi la chu xanh. aria-current do NavLink tu dat.
const linkClass = ({ isActive }) =>
  `whitespace-nowrap rounded px-2.5 py-1 ${isActive ? "bg-blue-100 font-semibold text-blue-800 ring-1 ring-blue-300" : "text-blue-700 hover:bg-slate-100"}`;

export default function App() {
  const { pathname } = useLocation();
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!getToken());

  useEffect(() => {
    if (!getToken()) return;
    api("/api/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setReady(true));
  }, []);

  // tieu de tab trinh duyet cung cho biet dang o trang nao
  useEffect(() => {
    const cur = NAV.filter(([, , roles]) => roles.includes(user?.role_name))
      .find(([to]) => (to === "/" ? pathname === "/" : pathname.startsWith(to)));
    document.title = cur ? `${cur[1]} · AI Invoice` : "AI Invoice";
  }, [pathname]);

  if (!ready) return null;
  if (!user) return <Login onLogin={setUser} />;

  const menu = NAV.filter(([, , roles]) => roles.includes(user.role_name));
  // trang chi danh cho mot so vai tro: vai tro khac bi dua ve trang chu
  const only = (roles, page) => (roles.includes(user.role_name) ? page : <Navigate to="/" replace />);

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="flex flex-wrap items-center gap-2 border-b bg-white px-6 py-3 text-sm">
        <b>AI Invoice</b>
        {menu.map(([to, label]) => <NavLink key={label} to={to} end={to === "/"} className={linkClass}>{label}</NavLink>)}
        <span className="ml-auto text-slate-600">{user.full_name} ({user.role_name})</span>
        <ThemeToggle />
        <button className="text-red-600" onClick={() => { setToken(null); setUser(null); }}>Đăng xuất</button>
      </nav>
      <main className="p-6">
        <UserContext.Provider value={user}>
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/review" element={only(["KTV"], <Review />)} />
            <Route path="/entries" element={only(["KTV"], <Entries />)} />
            <Route path="/approvals" element={only(["KTT"], <Approvals />)} />
            <Route path="/po" element={only(["KTV"], <PurchaseOrders />)} />
            <Route path="/export" element={only(["KTV", "KTT"], <Export />)} />
          </Routes>
        </UserContext.Provider>
      </main>
    </div>
  );
}
