// Dung chung cho Kiem tra va Dinh khoan: "lo" hoa don cua ke toan vien + nap truoc goi y but toan.
import { api } from "../../api/client.js";

export const BATCH = ["cho_xac_nhan", "da_luu", "tu_choi"];   // hoa don con trong cac lo kiem tra
// Hai lo rieng: lo MOI (vua tai len, cho xac nhan) va lo TU CHOI (bi ke toan truong tu choi, kiem tra lai)
export const lotOf = (x) => (x.status === "tu_choi" || (x.status === "da_luu" && x.reject_reason) ? "tu_choi" : "moi");
export const LOT_NAME = { moi: "lô mới", tu_choi: "lô từ chối" };

export const fetchQueue = () => api("/api/invoices?limit=200").then((r) => r.data
  .filter((x) => BATCH.includes(x.status))
  .map((x) => ({ invoice_id: x.invoice_id, status: x.status, reject_reason: x.reject_reason }))
  .sort((a, b) => a.invoice_id - b.invoice_id));

// Hoa don chua luu ke tiep trong lo (vong tron tu vi tri hien tai); het thi null
export function nextUnsavedIn(lotQ, curId) {
  const pos = lotQ.findIndex((q) => q.invoice_id === curId);
  return [...lotQ.slice(pos + 1), ...lotQ.slice(0, Math.max(pos, 0))]
    .find((q) => q.invoice_id !== curId && q.status !== "da_luu") || null;
}

// ---- Nap truoc goi y dinh khoan -------------------------------------------------------------------
// Goi y (ML/Gemini) mat vai giay den hang chuc giay, va bi gioi han toc do khi goi lien tuc. Thay vi doi den luc
// vao trang Dinh khoan, trong luc ke toan kiem tra truong cua hoa don hien tai, nen lan luot (MOI LUC 1 hoa don)
// xin goi y cho cac hoa don con lai cua lo va nho vao ban nhap (cung cho Entries.jsx dang dung) -> mo ra la co san.
const draftKey = (id) => `entries.draft.${id}`;
const PREFETCH_TIMEOUT_MS = 60000;
let order = [];
let running = false;
const done = new Set();
const inflight = new Map();

const hasDraft = (id) => { try { return !!sessionStorage.getItem(draftKey(id)); } catch { return false; } };
export const prefetchPromise = (id) => inflight.get(String(id)) || null;

async function one(id) {
  try {
    const j = await api(`/api/invoices/${id}/journal-entries`);
    if (!j.editable || j.data.length || hasDraft(id)) return;
    const r = await Promise.race([
      api(`/api/invoices/${id}/suggest-entries`, { method: "POST" }),
      new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), PREFETCH_TIMEOUT_MS)),
    ]);
    // goi y chi la "mac dinh" (AI khong tra loi/het luot) thi KHONG nho: de trang Dinh khoan hoi lai AI khi mo
    if (r.data?.length && r.data[0].source !== "rule") sessionStorage.setItem(draftKey(id), JSON.stringify(r.data.map((e) => ({ ...e, edited: false, prefetched: true }))));
  } catch { /* loi / het han: de trang Dinh khoan tu hoi AI khi mo */ }
}

async function pump() {
  if (running) return;
  running = true;
  while (order.length) {
    const id = order.shift();
    if (done.has(id) || inflight.has(id)) continue;
    const p = one(id);
    inflight.set(id, p);
    await p;
    inflight.delete(id);
    done.add(id);
  }
  running = false;
}

// ids theo thu tu uu tien (hoa don sap toi truoc). Goi lai nhieu lan thi chi doi thu tu hang cho.
export function prefetchSuggestions(ids) {
  order = ids.map(String).filter((id) => !done.has(id) && !inflight.has(id));
  pump();
}
