import { useEffect, useState } from "react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { api, getToken, setToken } from "./api/client.js";
import ThemeToggle from "./components/ThemeToggle.jsx";
import Login from "./pages/Login.jsx";
// import Register from "./pages/Register.jsx";
import {
  Approvals,
  Entries,
  Export,
  PurchaseOrders,
  Review,
  Upload,
} from "./pages/pages.jsx";

// Chu so huu khung giao dien (nav, bao ve route theo vai tro): Duong (C9)
const NAV = [
  ["/", "Tải hóa đơn"],
  ["/review", "Kiểm tra"],
  ["/entries", "Bút toán"],
  ["/approvals", "Hàng chờ duyệt"],
  ["/po", "PO"],
  ["/export", "Xuất"],
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
    api("/api/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  // tieu de tab trinh duyet cung cho biet dang o trang nao
  useEffect(() => {
    const cur = NAV.find(([to]) =>
      to === "/" ? pathname === "/" : pathname.startsWith(to),
    );
    document.title = cur ? `${cur[1]} · AI Invoice` : "AI Invoice";
  }, [pathname]);

  if (!ready) return null;
  if (!user)
    return pathname === "/register" ? (
      <Register onLogin={setUser} />
    ) : (
      <Login onLogin={setUser} />
    );

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="flex flex-wrap items-center gap-2 border-b bg-white px-6 py-3 text-sm">
        <b>AI Invoice</b>
        {NAV.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/"} className={linkClass}>
            {to === "/" && !user.can_work ? "Hóa đơn" : label}
          </NavLink>
        ))}
        <span className="ml-auto text-slate-600">
          {user.full_name} ({user.role_name})
        </span>
        <ThemeToggle />
        <button
          className="text-red-600"
          onClick={() => {
            setToken(null);
            setUser(null);
          }}
        >
          Đăng xuất
        </button>
      </nav>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Upload user={user} />} />
          <Route path="/review" element={<Review />} />
          <Route path="/entries" element={<Entries />} />
          {/* Chi KTT vao duoc hang cho duyet */}
          <Route
            path="/approvals"
            element={
              user.role_name === "KTT" ? <Approvals /> : <Navigate to="/" />
            }
          />
          <Route path="/po" element={<PurchaseOrders />} />
          <Route path="/export" element={<Export />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
