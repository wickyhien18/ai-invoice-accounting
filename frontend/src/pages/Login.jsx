import { useState } from "react";
import { api, setToken } from "../api/client.js";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("ktv@demo.local");
  const [password, setPassword] = useState("ktv12345");
  const [err, setErr] = useState("");

  async function submit(e) {
    e.preventDefault();
    try {
      const r = await api("/api/auth/login", { method: "POST", body: { email, password } });
      setToken(r.access_token);
      onLogin(r.user);
    } catch (ex) {
      setErr(ex.message);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-24 w-80 space-y-3 rounded border bg-white p-6">
      <h1 className="text-lg font-semibold">Đăng nhập</h1>
      <input className="w-full rounded border p-2" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" className="w-full rounded border p-2" value={password} onChange={(e) => setPassword(e.target.value)} />
      {err && <p className="text-sm text-red-600">{err}</p>}
      <button className="w-full rounded bg-blue-600 p-2 text-white">Đăng nhập</button>
      <p className="text-xs text-slate-500">Tài khoản demo: xem SETUP.md (seed_demo.py)</p>
    </form>
  );
}
