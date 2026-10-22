"""B4: sinh du lieu GIA de huan luyen hai mo hinh cua Goi B. Chay tu thu muc goc du an:

    python tools/gen_gl_data.py            # ghi ai-service/data/gl_training.csv va doc_training.csv
    python tools/gen_gl_data.py --seed 7   # doi hat giong de thu do on dinh

1) gl_training.csv  - moi dong la mot hoa don da dinh khoan: nguoi ban, thue suat, tien truoc thue,
   tong tien -> tai khoan No (khoan muc chinh) va Co theo TT133. Co cot vendor_id de CHIA TAP THEO NGUOI BAN
   (do chinh xac tren nguoi ban chua tung thay moi la so dang tin, khong phai tren tap tron ngau nhien).
2) doc_training.csv - van ban kieu OCR cua nhieu loai chung tu (B8), co nhieu (mat dau, sai ky tu, bo dong).

QUAN TRONG: day la quy tac do NHOM TU DAT, khong phai thuc te ke toan cua doanh nghiep nao. So lieu do tren
bo nay chi chung minh luong hoat dong, khong noi len do chinh xac tren du lieu that.
"""
import argparse
import csv
import random
import unicodedata
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "ai-service" / "data"

# ---------------------------------------------------------------- nguoi ban
# (cum tu nganh trong ten, ham chon (No, Co) -> sinh o duoi). Ten cong ty theo dung kieu bo hoa don gia.
PREFIX = ["Công ty TNHH", "Công ty CP", "Công ty TNHH MTV", "Doanh nghiệp tư nhân"]
GIVEN = ["Dũng", "Bình", "Quang", "Cường", "Tâm", "Minh", "Lan", "Hùng", "Phúc", "Nam", "Hà", "Sơn", "Thảo",
         "Long", "Vinh", "Hải", "Trang", "Khoa", "Yến", "Đạt", "Mai", "Thịnh", "An", "Linh"]

# nganh -> (cac cum tu trong ten, thue suat co the, tien truoc thue (min, max), kich thuoc nhom)
INDUSTRIES = {
    "van_phong_pham": (["Văn phòng phẩm", "Văn phòng phẩm và Thiết bị trường học"], [8, 10], (200_000, 12_000_000)),
    "thiet_bi_it": (["Thiết bị IT", "Máy tính và Thiết bị mạng", "Công nghệ Thiết bị số"], [8, 10], (1_500_000, 90_000_000)),
    "noi_that": (["Nội thất", "Nội thất văn phòng", "Nội thất và Trang trí"], [8, 10], (1_000_000, 80_000_000)),
    "van_tai": (["Vận tải", "Vận tải và Logistics", "Giao nhận Vận chuyển"], [8, 10], (500_000, 30_000_000)),
    "in_an_qc": (["In ấn", "Quảng cáo và In ấn", "Truyền thông Quảng cáo"], [8, 10], (300_000, 25_000_000)),
    "thuc_pham": (["Thực phẩm", "Thực phẩm và Đồ uống", "Nước uống Thực phẩm"], [5, 8, 10], (100_000, 15_000_000)),
    "dien_nuoc_vt": (["Điện lực", "Viễn thông", "Cấp nước", "Internet Viễn thông"], [8, 10], (300_000, 20_000_000)),
    "nguyen_lieu": (["Nguyên liệu", "Vật liệu Thép", "Hạt nhựa Nguyên liệu", "Vật tư Công nghiệp"], [8, 10], (2_000_000, 120_000_000)),
    "bao_hiem_thue": (["Bảo hiểm", "Bất động sản cho thuê", "Quản lý Tòa nhà"], [0, 8, 10], (3_000_000, 150_000_000)),
    "tu_van": (["Tư vấn", "Kiểm toán và Tư vấn", "Pháp lý Tư vấn", "Đào tạo Tư vấn"], [8, 10], (2_000_000, 60_000_000)),
    "tai_chinh": (["Tài chính", "Cho thuê Tài chính"], [0], (500_000, 40_000_000)),
    "dich_vu": (["Dịch vụ", "Dịch vụ Thương mại", "Dịch vụ Tổng hợp"], [5, 8, 10], (200_000, 20_000_000)),
}
# So nguoi ban moi nganh (nganh "dich_vu" cố ý nhieu hon: ten mo ho, tai khoan phu thuoc tung nguoi ban)
VENDORS_PER = {k: 5 for k in INDUSTRIES} | {"dich_vu": 9, "van_tai": 7, "thuc_pham": 6}
ROWS_PER_VENDOR = (4, 14)
NOISE = 0.05          # ti le dong bi gan tai khoan "la" (ke toan hach toan khac thuong le)
PAID_NOW_SHARE = 0.18  # ti le nguoi ban hay tra ngay (co 111/112 thay 331)

TT133_ALL = ["111", "112", "131", "141", "152", "153", "156", "211", "242", "331", "627", "635", "642", "6421", "6422", "811"]


def pick_debit(industry: str, amount: int, habit: str) -> str:
    """Tai khoan No cua dong chinh (chua gom thue GTGT 1331). `habit` la thoi quen rieng cua nguoi ban."""
    if industry == "van_phong_pham":
        return "6422" if amount < 3_000_000 else "153"
    if industry in ("thiet_bi_it", "noi_that"):
        return "211" if amount >= 30_000_000 else ("153" if amount >= 3_000_000 else "6422")
    if industry == "van_tai":
        return habit  # 6421 (ban hang) hoac 627 (san xuat chung): tuy cong ty dung xe cho muc dich nao
    if industry == "in_an_qc":
        return "6421"
    if industry == "thuc_pham":
        return habit  # 156 (hang hoa) hoac 6422 (tiep khach, van phong)
    if industry == "dien_nuoc_vt":
        return "6422"
    if industry == "nguyen_lieu":
        return "152"
    if industry == "bao_hiem_thue":
        return "242" if amount >= 20_000_000 else "6422"
    if industry == "tu_van":
        return "6422"
    if industry == "tai_chinh":
        return "635"
    return habit      # dich_vu: ten mo ho -> moi nguoi ban mot kieu


HABITS = {"van_tai": ["6421", "627"], "thuc_pham": ["156", "6422"], "dich_vu": ["6422", "6422", "6421", "627", "6422"]}


def make_vendors(rng: random.Random) -> list[dict]:
    vendors, used = [], set()
    for industry, (phrases, rates, _) in INDUSTRIES.items():
        for _ in range(VENDORS_PER[industry]):
            while True:
                name = f"{rng.choice(PREFIX)} {rng.choice(phrases)} Mẫu Thử {rng.choice(GIVEN)}"
                if name not in used:
                    used.add(name)
                    break
            mst = "0" + "".join(rng.choice("0123456789") for _ in range(9))
            vendors.append({
                "vendor_id": len(vendors) + 1, "seller_name": name, "mst_seller": mst, "industry": industry,
                "habit": rng.choice(HABITS.get(industry, ["6422"])),
                "rate_pool": rates, "paid_now": rng.random() < PAID_NOW_SHARE,
                "pay_account": rng.choice(["111", "112"]),
            })
    return vendors


def make_gl_rows(rng: random.Random) -> list[dict]:
    rows = []
    for v in make_vendors(rng):
        lo, hi = INDUSTRIES[v["industry"]][2]
        for _ in range(rng.randint(*ROWS_PER_VENDOR)):
            before = int(round(rng.uniform(lo, hi) / 100) * 100) if rng.random() < 0.5 else \
                int(round(lo * (hi / lo) ** rng.random() / 100) * 100)  # tron deu + lech ve gia tri nho
            rate = rng.choice(v["rate_pool"])
            vat = round(before * rate / 100)
            debit = pick_debit(v["industry"], before, v["habit"])
            credit = v["pay_account"] if (v["paid_now"] and before < 10_000_000) else "331"
            if rng.random() < NOISE:
                debit = rng.choice([a for a in ("153", "156", "6421", "6422", "627", "642") if a != debit])
            rows.append({
                "vendor_id": v["vendor_id"], "seller_name": v["seller_name"], "mst_seller": v["mst_seller"],
                "vat_rate": rate, "total_before_tax": before, "vat_amount": vat, "total_amount": before + vat,
                "debit_account": debit, "credit_account": credit,
            })
    rng.shuffle(rows)
    return rows


# ---------------------------------------------------------------- B8: loai chung tu
DOC_TEMPLATES = {
    "hoa_don_gtgt": [
        ["HÓA ĐƠN GIÁ TRỊ GIA TĂNG", "(VAT INVOICE)", "Ký hiệu: {ks}", "Số: {so}", "Mã số thuế: {mst}",
         "Thuế suất GTGT: {thue}%", "Tiền thuế GTGT: {tt}", "Tổng cộng tiền thanh toán: {tong}"],
        ["HÓA ĐƠN GTGT", "Mẫu số 01GTKT", "Ký hiệu {ks}", "Số {so}", "MST người bán: {mst}",
         "Cộng tiền hàng: {tong}", "Thuế GTGT {thue}%", "Số tiền viết bằng chữ"],
    ],
    "hoa_don_ban_hang": [
        ["HÓA ĐƠN BÁN HÀNG", "Ký hiệu: {ks}", "Số: {so}", "Mã số thuế: {mst}",
         "Không chịu thuế GTGT", "Cộng tiền hàng: {tong}", "Tổng số tiền thanh toán: {tong}"],
        ["HÓA ĐƠN BÁN HÀNG (SALES INVOICE)", "Số {so}", "MST {mst}", "Tổng cộng: {tong}", "Người bán hàng"],
    ],
    "bien_lai_phieu_thu": [
        ["BIÊN LAI THU TIỀN", "Số: {so}", "Người nộp tiền", "Số tiền: {tong}", "Lý do nộp", "Người thu tiền"],
        ["PHIẾU THU", "Quyển số", "Số: {so}", "Họ tên người nộp tiền", "Số tiền: {tong}", "Kế toán trưởng"],
    ],
    "phieu_giao_hang_xuat_kho": [
        ["PHIẾU XUẤT KHO", "Số: {so}", "Họ tên người nhận hàng", "Xuất tại kho", "Số lượng thực xuất", "Thủ kho"],
        ["PHIẾU GIAO HÀNG", "Số {so}", "Đơn vị vận chuyển", "Người nhận hàng ký tên", "Số lượng", "Đơn vị tính"],
    ],
    "bao_gia_hop_dong": [
        ["BẢNG BÁO GIÁ", "Số: {so}", "Kính gửi quý khách hàng", "Đơn giá chưa bao gồm VAT", "Báo giá có hiệu lực 30 ngày"],
        ["HỢP ĐỒNG KINH TẾ", "Số: {so}/HĐKT", "Bên A", "Bên B", "Điều 1: Nội dung hợp đồng", "Điều 2: Giá trị hợp đồng {tong}"],
    ],
    "khac": [
        ["THƯ MỜI HỌP", "Kính mời", "Thời gian", "Địa điểm họp", "Trân trọng"],
        ["BIÊN BẢN HỌP", "Thành phần tham dự", "Nội dung cuộc họp", "Thư ký ghi biên bản"],
        ["DANH SÁCH NHÂN SỰ", "STT", "Họ và tên", "Phòng ban", "Ngày vào làm"],
    ],
}
ITEMS = ["Giấy in A4", "Bút bi", "Mực in", "Ghế xoay", "Cước internet", "Phí vận chuyển", "Nước uống", "Tiền thuê"]


def strip_accents(s: str) -> str:
    s = s.replace("Đ", "D").replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def ocr_noise(lines: list[str], rng: random.Random) -> str:
    out = []
    mode = rng.random()
    for ln in lines:
        if rng.random() < 0.12:
            continue  # mat dong
        if mode < 0.35:
            ln = strip_accents(ln)  # OCR mat dau
        elif mode < 0.5:
            ln = ln.upper()
        if rng.random() < 0.2:
            ln = ln.replace("0", "O").replace("1", "l")
        if rng.random() < 0.15 and len(ln) > 6:
            i = rng.randrange(len(ln))
            ln = ln[:i] + ln[i + 1:]  # roi mot ky tu
        out.append(ln)
    return "\n".join(out) or "..."


def make_doc_rows(rng: random.Random, per_class: int) -> list[dict]:
    rows = []
    for label, templates in DOC_TEMPLATES.items():
        for _ in range(per_class):
            tpl = rng.choice(templates)
            vals = {"ks": rng.choice(["C26TAA", "K26TPA", "C26MBF", "1C26TYY"]), "so": f"{rng.randint(1, 999999):07d}",
                    "mst": "0" + "".join(rng.choice("0123456789") for _ in range(9)), "thue": rng.choice([0, 5, 8, 10]),
                    "tt": f"{rng.randint(10, 9000) * 1000:,}".replace(",", "."),
                    "tong": f"{rng.randint(100, 90000) * 1000:,}".replace(",", ".")}
            lines = [t.format(**vals) for t in tpl]
            for _ in range(rng.randint(0, 3)):  # dong hang chung chung, giong nhau o moi loai
                lines.insert(rng.randrange(1, len(lines) + 1), f"{rng.choice(ITEMS)} {rng.randint(1, 20)} {rng.randint(10, 900) * 1000}")
            rows.append({"text": ocr_noise(lines, rng), "doc_type": label})
    rng.shuffle(rows)
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    gl = make_gl_rows(rng)
    doc = make_doc_rows(rng, 70)
    write_csv(a.out / "gl_training.csv", gl)
    write_csv(a.out / "doc_training.csv", doc)
    print(f"gl_training.csv: {len(gl)} dong, {len({r['vendor_id'] for r in gl})} nguoi ban -> {a.out}")
    print(f"doc_training.csv: {len(doc)} dong, {len(DOC_TEMPLATES)} loai")


if __name__ == "__main__":
    main()
