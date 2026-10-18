import { useSyncExternalStore } from "react";

// Che do sang/toi: luu o localStorage, mac dinh theo he dieu hanh. Dung chung cho moi noi cam nut doi.
const KEY = "theme";
const listeners = new Set();

function stored() {
  try { return localStorage.getItem(KEY); } catch { return null; }
}
function systemDark() {
  return typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: dark)").matches;
}
function current() {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}
function apply(mode) {
  document.documentElement.classList.toggle("dark", mode === "dark");
  listeners.forEach((l) => l());
}

export function initTheme() {
  const saved = stored();
  apply(saved === "dark" || saved === "light" ? saved : systemDark() ? "dark" : "light");
  // chua tu chon thi theo he dieu hanh khi no doi
  if (typeof matchMedia === "function") {
    matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", (e) => {
      if (!stored()) apply(e.matches ? "dark" : "light");
    });
  }
}

export function setTheme(mode) {
  try { localStorage.setItem(KEY, mode); } catch { /* trinh duyet chan luu tru: van doi duoc trong phien nay */ }
  apply(mode);
}

export function useTheme() {
  const mode = useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => listeners.delete(cb); },
    current,
    () => "light",
  );
  return [mode, (m) => setTheme(m ?? (mode === "dark" ? "light" : "dark"))];
}
