import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { api, getToken, setToken } from "./api/client.js";
import Login from "./pages/Login.jsx";
import { Approvals, Entries, Export, PurchaseOrders, Review, Upload } from "./pages/pages.jsx";

// Chu so huu khung giao dien (nav, bao ve route theo vai tro): Duong (C9)
const NAV = [
  ["/", "Tải hóa đơn"], ["/review", "Kiểm tra"], ["/entries", "Bút toán"],
  ["/approvals", "Hàng chờ duyệt"], ["/po", "PO"], ["/export", "Xuất"],
];

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!getToken());

  useEffect(() => {
    if (!getToken()) return;
    api("/api/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setReady(true));
  }, []);

  if (!ready) return null;
  if (!user) return <Login onLogin={setUser} />;

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="flex items-center gap-4 border-b bg-white px-6 py-3 text-sm">
        <b>AI Invoice</b>
        {NAV.map(([to, label]) => <Link key={to} to={to} className="text-blue-700">{label}</Link>)}
        <span className="ml-auto text-slate-600">{user.full_name} ({user.role_name})</span>
        <button className="text-red-600" onClick={() => { setToken(null); setUser(null); }}>Đăng xuất</button>
      </nav>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/review" element={<Review />} />
          <Route path="/entries" element={<Entries />} />
          {/* Chi KTT vao duoc hang cho duyet */}
          <Route path="/approvals" element={user.role_name === "KTT" ? <Approvals /> : <Navigate to="/" />} />
          <Route path="/po" element={<PurchaseOrders />} />
          <Route path="/export" element={<Export />} />
        </Routes>
      </main>
    </div>
  );
}
