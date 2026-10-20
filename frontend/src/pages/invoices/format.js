// Dinh dang hien thi dung chung cho cac trang hoa don (Goi A).
export const STATUS = {
  dang_xu_ly: ["Đang xử lý", "bg-blue-100 text-blue-800"],
  loi_xu_ly: ["Lỗi xử lý", "bg-red-100 text-red-800"],
  cho_xac_nhan: ["Chờ xác nhận", "bg-amber-100 text-amber-800"],
  cho_duyet: ["Chờ duyệt", "bg-violet-100 text-violet-800"],
  da_duyet: ["Đã duyệt", "bg-green-100 text-green-800"],
  tu_choi: ["Từ chối", "bg-slate-200 text-slate-700"],
};

export const FILE_TYPE = { pdf: "PDF", image: "Ảnh", xml: "XML" };

export function money(v) {
  if (v === null || v === undefined || v === "") return "—";
  return new Intl.NumberFormat("vi-VN").format(Number(v));
}

export function dateVN(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
