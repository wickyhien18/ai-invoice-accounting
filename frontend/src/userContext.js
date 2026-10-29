// Nguoi dung dang dang nhap, dung chung cho moi trang (khong phai truyen prop qua tung cap).
// Vai tro: KTV (ke toan vien) lam viec nhap lieu; KTT (ke toan truong) duyet va xoa. Backend van la noi chan quyen that.
import { createContext, useContext } from "react";

export const UserContext = createContext(null);
export const useUser = () => useContext(UserContext);
export const isKTV = (u) => u?.role_name === "KTV";
export const isKTT = (u) => u?.role_name === "KTT";
