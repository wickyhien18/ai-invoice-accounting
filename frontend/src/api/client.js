// Ham goi API dung chung. Token luu o localStorage (chi cho phat trien).
const KEY = "token";
export const getToken = () => localStorage.getItem(KEY);
export const setToken = (t) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY));

function authHeaders(extra = {}) {
  const t = getToken();
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

async function fail(res) {
  const d = (await res.json().catch(() => ({}))).detail;
  throw new Error(typeof d === "string" ? d : `Lỗi ${res.status}`);
}

// body la object -> gui JSON; body la FormData -> gui multipart (de trinh duyet tu dat Content-Type)
export async function api(path, { method = "GET", body } = {}) {
  const isForm = body instanceof FormData;
  const res = await fetch(path, {
    method,
    headers: authHeaders(isForm ? {} : { "Content-Type": "application/json" }),
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });
  if (!res.ok) await fail(res);
  return res.json();
}

// Tai file can dang nhap (VD anh hoa don): the <img>/<a> khong gui duoc token, nen lay blob roi tao URL tam.
export async function fetchBlobUrl(path) {
  const res = await fetch(path, { headers: authHeaders() });
  if (!res.ok) await fail(res);
  return URL.createObjectURL(await res.blob());
}
