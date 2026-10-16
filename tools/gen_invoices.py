#!/usr/bin/env python3
"""Tao bo hoa don GTGT GIA de thu nghiem OCR/LLM (khong dung du lieu that).

Dau ra trong thu muc --out:
  pdf/      hoa don dang PDF (sach)
  images/   anh PNG; mot phan bi lam nhieu (nghieng, mo, nhieu, toi) de giong anh chup dien thoai
  xml/      file XML mo phong cau truc hoa don dien tu (don gian hoa, CHUA kiem tra voi XSD chinh thuc)
  labels.json, labels.csv   dap an chuan de cham diem

Moi ten cong ty, MST, dia chi deu la du lieu gia. Moi hoa don co dong chu nho "DU LIEU GIA - CHI DUNG THU NGHIEM".
Yeu cau: pip install reportlab pillow numpy ; can pdftoppm (poppler) de doi PDF sang anh.

Chay:  python gen_invoices.py --n 40 --out data_test --seed 1 [--style portal]

Ghi chu nhan: mau_so = '1' va ky_hieu = 'C26TAA' (khong gom mau so). Mot so hoa don hien thi 'Ky hieu: 1C26TAA'.
"""
import argparse, csv, json, random, subprocess, os
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("VN", FONT_DIR + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("VN-B", FONT_DIR + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("VN-S", FONT_DIR + "DejaVuSerif.ttf"))
pdfmetrics.registerFont(TTFont("VN-SB", FONT_DIR + "DejaVuSerif-Bold.ttf"))

SELLER_NAMES = ["Công ty TNHH Thương mại Mẫu Thử An", "Công ty CP Dịch vụ Mẫu Thử Bình", "Công ty TNHH Văn phòng phẩm Mẫu Thử Cường",
                "Công ty CP Vận tải Mẫu Thử Dũng", "Công ty TNHH Điện máy Mẫu Thử Hà", "Công ty CP Thực phẩm Mẫu Thử Lan",
                "Công ty TNHH In ấn Mẫu Thử Minh", "Công ty CP Viễn thông Mẫu Thử Nam", "Công ty TNHH Xây dựng Mẫu Thử Phát",
                "Công ty TNHH Thiết bị IT Mẫu Thử Quang", "Công ty CP Du lịch Mẫu Thử Sơn", "Công ty TNHH Nội thất Mẫu Thử Tâm"]
STREETS = ["Nguyễn Trãi", "Lê Duẩn", "Trần Phú", "Giải Phóng", "Cầu Giấy", "Láng Hạ", "Nguyễn Văn Linh", "Điện Biên Phủ", "Lê Lợi", "Phạm Văn Đồng"]
CITIES = ["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ"]
BUYER = ("Công ty TNHH Khách Hàng Mẫu Thử", "0109999990", "Số 1 Đường Thử Nghiệm, Phường Mẫu, Quận Giả, Hà Nội")
ITEMS = [("Giấy in A4 Double A 70gsm", "Ream", 62000, 90000), ("Bút bi Thiên Long TL-027", "Cái", 3000, 6000),
         ("Mực in HP 12A", "Hộp", 850000, 1300000), ("Dịch vụ vận chuyển hàng hóa", "Chuyến", 300000, 2500000),
         ("Cước internet cáp quang tháng", "Tháng", 250000, 1200000), ("Chuột không dây Logitech M331", "Cái", 180000, 320000),
         ("Bàn làm việc 1m2", "Cái", 1500000, 3200000), ("Dịch vụ in ấn tài liệu", "Trang", 500, 2000),
         ("Nước uống đóng bình 20L", "Bình", 45000, 80000), ("Phí bảo trì máy tính", "Lần", 200000, 900000),
         ("Vé máy bay nội địa", "Vé", 1100000, 3500000), ("Tiền thuê phòng họp", "Giờ", 150000, 600000),
         ("Máy tính xách tay Dell Vostro", "Chiếc", 14000000, 19000000), ("Ghế xoay văn phòng", "Cái", 650000, 1800000)]
DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def read3(n, full):
    tram, chuc, dv = n // 100, (n // 10) % 10, n % 10
    s = []
    if tram or full:
        s.append(DIGITS[tram] + " trăm")
    if chuc == 0 and dv and (tram or full):
        s.append("lẻ")
    if chuc >= 2:
        s.append(DIGITS[chuc] + " mươi")
    elif chuc == 1:
        s.append("mười")
    if dv:
        if chuc >= 2 and dv == 1:
            s.append("mốt")
        elif chuc >= 1 and dv == 5:
            s.append("lăm")
        else:
            s.append(DIGITS[dv])
    return " ".join(s)


def money_words(n):
    if n == 0:
        return "Không đồng"
    units = ["", " nghìn", " triệu", " tỷ"]
    parts, i, started = [], 0, False
    groups = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    out = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            started = True
            continue
        out.append(read3(g, started and i != len(groups) - 1) + units[i])
        started = True
    s = " ".join(out).strip()
    return s[0].upper() + s[1:] + " đồng"


def fmt(n):
    return f"{n:,}".replace(",", ".")


def fake_mst(rng):
    return "0" + "".join(str(rng.randint(0, 9)) for _ in range(9))


def fake_code(rng, n, alphabet="0123456789ABCDEF"):
    return "".join(rng.choice(alphabet) for _ in range(n))


def make_invoice(rng, idx, style_mode="mix"):
    seller = rng.choice(SELLER_NAMES)
    has_code = rng.random() < 0.6  # ky hieu bat dau bang C (co ma cua co quan thue) hoac K (khong ma)
    ky_hieu = f"{'C' if has_code else 'K'}26{rng.choice(['T', 'T', 'M'])}{rng.choice('ABCDEFGHKLMNPQRSTUVXY')}{rng.choice('ABCDEFGHKLMNPQRSTUVXY')}"
    n_lines = rng.randint(1, 6)
    lines, subtotal = [], 0
    for name, unit, lo, hi in rng.sample(ITEMS, n_lines):
        qty = rng.randint(1, 20) if hi < 100000 else rng.randint(1, 5)
        price = round(rng.randint(lo, hi), -2 if lo >= 1000 else 0)
        amount = qty * price
        lines.append({"ten_hang": name, "dvt": unit, "so_luong": qty, "don_gia": price, "thanh_tien": amount})
        subtotal += amount
    rate = rng.choice([8, 10, 10, 5, 0])
    tax = round(subtotal * rate / 100)
    d = date(2026, 1, 1) + timedelta(days=rng.randint(0, 270))
    return {
        "id": f"HD{idx:03d}",
        "mau_so": "1", "ky_hieu": ky_hieu,
        "ma_co_quan_thue": ("MẪU-THỬ-" + fake_code(rng, 12)) if has_code else "",
        "ma_tra_cuu": fake_code(rng, 8, "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"),
        "stk_nguoi_ban": "".join(str(rng.randint(0, 9)) for _ in range(12)),
        "ngan_hang": "Ngân hàng TMCP Mẫu Thử",
        "so_hoa_don": f"{rng.randint(1, 9999999):07d}",
        "ngay_lap": d.strftime("%d/%m/%Y"),
        "ten_nguoi_ban": seller, "mst_nguoi_ban": fake_mst(rng),
        "dia_chi_nguoi_ban": f"Số {rng.randint(1, 300)} đường {rng.choice(STREETS)}, {rng.choice(CITIES)}",
        "ten_nguoi_mua": BUYER[0], "mst_nguoi_mua": BUYER[1], "dia_chi_nguoi_mua": BUYER[2],
        "hinh_thuc_tt": rng.choice(["TM/CK", "Chuyển khoản", "Tiền mặt"]),
        "dong_hang": lines, "tong_truoc_thue": subtotal, "thue_suat": rate, "tien_thue": tax,
        "tong_thanh_toan": subtotal + tax, "bang_chu": money_words(subtotal + tax),
        "mau_trinh_bay": "P" if style_mode == "portal" else rng.choice(["A", "B", "C", "P", "P"]),
    }


def draw_portal(inv, path):
    """Kieu the hien hoa don dien tu GTGT theo bo cuc pho bien (song ngu Viet-Anh, hang danh so cot,
    khung chu ky so, ma co quan thue, ma tra cuu). Tu dung lai theo bo cuc chung, KHONG sao chep
    hoa don cua doanh nghiep nao. Chu ky so, ma co quan thue, website deu la gia va ghi ro la mau."""
    W, H = A4
    c = canvas.Canvas(str(path), pagesize=A4)
    L, R = 32, W - 32
    f, fb = "VN", "VN-B"
    # hinh chim "MAU THU NGHIEM" rat nhat
    c.saveState(); c.setFillGray(0.93); c.setFont(fb, 60)
    c.translate(W / 2, H / 2); c.rotate(35); c.drawCentredString(0, 0, "MẪU THỬ NGHIỆM"); c.restoreState()
    c.setFillGray(0)
    y = H - 42
    # khung logo gia
    c.setDash(2, 2); c.setStrokeGray(0.6); c.rect(L, y - 46, 62, 46); c.setDash(); c.setStrokeGray(0)
    c.setFont(f, 7); c.setFillGray(0.5); c.drawCentredString(L + 31, y - 26, "LOGO"); c.setFillGray(0)
    tx = L + 74
    c.setFont(fb, 10.5); c.drawString(tx, y - 8, inv["ten_nguoi_ban"].upper())
    c.setFont(f, 8.5)
    c.drawString(tx, y - 21, "Mã số thuế (Tax code): " + inv["mst_nguoi_ban"])
    c.drawString(tx, y - 32, "Địa chỉ (Address): " + inv["dia_chi_nguoi_ban"])
    c.drawString(tx, y - 43, "Điện thoại (Tel): 024 3xxx xxxx    Số tài khoản (Account No.): " + inv["stk_nguoi_ban"])
    c.drawString(tx, y - 54, "Ngân hàng (Bank): " + inv["ngan_hang"])
    y -= 74
    c.setLineWidth(0.6); c.line(L, y, R, y); y -= 22
    # tieu de + khung ky hieu
    c.setFont(fb, 15); c.drawCentredString(W / 2 - 40, y, "HÓA ĐƠN GIÁ TRỊ GIA TĂNG")
    c.setFont(f, 9); c.drawCentredString(W / 2 - 40, y - 12, "(VAT INVOICE)")
    d, m, yy = inv["ngay_lap"].split("/")
    c.drawCentredString(W / 2 - 40, y - 26, f"Ngày (date) {d} tháng (month) {m} năm (year) {yy}")
    bx = R - 138
    c.rect(bx, y - 36, 138, 50)
    c.setFont(f, 8.5); c.drawString(bx + 6, y + 3, "Mẫu số (Form): " + inv["mau_so"])
    c.drawString(bx + 6, y - 9, "Ký hiệu (Serial): " + inv["ky_hieu"])
    c.drawString(bx + 6, y - 21, "Số (No.): "); c.setFont(fb, 10); c.setFillColorRGB(0.75, 0, 0)
    c.drawString(bx + 50, y - 21, inv["so_hoa_don"]); c.setFillGray(0)
    y -= 56
    # nguoi mua
    c.setFont(f, 8.5)
    for lab, val in [("Họ tên người mua hàng (Buyer): ", ""), ("Tên đơn vị (Company's name): ", inv["ten_nguoi_mua"]),
                     ("Mã số thuế (Tax code): ", inv["mst_nguoi_mua"]), ("Địa chỉ (Address): ", inv["dia_chi_nguoi_mua"]),
                     ("Hình thức thanh toán (Payment method): ", inv["hinh_thuc_tt"]), ("Số tài khoản (Account No.): ", "")]:
        c.drawString(L, y, lab + val); y -= 12
    y -= 6
    # bang hang, tieu de 2 dong song ngu + hang danh so cot
    cols = [("STT", "(No.)", 28), ("Tên hàng hóa, dịch vụ", "(Description)", 197), ("Đơn vị tính", "(Unit)", 58),
            ("Số lượng", "(Quantity)", 55), ("Đơn giá", "(Unit price)", 85), ("Thành tiền", "(Amount)", 100)]
    tw = sum(w for *_, w in cols)
    hh = 28
    c.setFillGray(0.92); c.rect(L, y - hh, tw, hh, fill=1, stroke=1); c.setFillGray(0)
    x = L
    for a, b, w in cols:
        c.setFont(fb, 8); c.drawCentredString(x + w / 2, y - 11, a)
        c.setFont(f, 7.5); c.drawCentredString(x + w / 2, y - 22, b)
        if x > L: c.line(x, y, x, y - hh)
        x += w
    y -= hh
    rowh = 17
    nums = ["1", "2", "3", "4", "5", "6=4x5"]
    x = L
    for (a, b, w), t in zip(cols, nums):
        c.rect(x, y - 13, w, 13); c.setFont("VN", 7.5); c.drawCentredString(x + w / 2, y - 10, t); x += w
    y -= 13
    lines = inv["dong_hang"]
    total_rows = max(8, len(lines))
    for i in range(total_rows):
        vals = [""] * 6
        if i < len(lines):
            ln = lines[i]
            vals = [str(i + 1), ln["ten_hang"], ln["dvt"], fmt(ln["so_luong"]), fmt(ln["don_gia"]), fmt(ln["thanh_tien"])]
        x = L
        for k, ((a, b, w), v) in enumerate(zip(cols, vals)):
            c.rect(x, y - rowh, w, rowh); c.setFont(f, 8.5)
            if k == 1: c.drawString(x + 4, y - 12, v)
            elif k >= 3: c.drawRightString(x + w - 4, y - 12, v)
            else: c.drawCentredString(x + w / 2, y - 12, v)
            x += w
        y -= rowh
    # tong
    def total_row(label, value, bold=False):
        nonlocal y
        c.rect(L, y - rowh, tw, rowh)
        c.setFont(fb if bold else f, 8.5)
        c.drawString(L + 6, y - 12, label); c.drawRightString(L + tw - 4, y - 12, value); y -= rowh
    total_row("Cộng tiền hàng (Total amount):", fmt(inv["tong_truoc_thue"]))
    total_row(f"Thuế suất GTGT (VAT rate): {inv['thue_suat']}%        Tiền thuế GTGT (VAT amount):", fmt(inv["tien_thue"]))
    total_row("Tổng tiền thanh toán (Total payment):", fmt(inv["tong_thanh_toan"]), True)
    c.rect(L, y - rowh, tw, rowh); c.setFont(f, 8.5)
    c.drawString(L + 6, y - 12, "Số tiền viết bằng chữ (Total amount in words): " + inv["bang_chu"]); y -= rowh + 14
    # chu ky
    c.setFont(fb, 9); c.drawCentredString(L + 110, y, "Người mua hàng (Buyer)")
    c.drawCentredString(R - 120, y, "Người bán hàng (Seller)")
    c.setFont(f, 7.5)
    c.drawCentredString(L + 110, y - 11, "(Ký, ghi rõ họ tên) (Sign & full name)")
    c.drawCentredString(R - 120, y - 11, "(Chữ ký điện tử, chữ ký số) (Digital signature)")
    sy = y - 26
    c.setStrokeColorRGB(0.1, 0.5, 0.1); c.setLineWidth(1)
    c.rect(R - 235, sy - 56, 230, 56); c.setStrokeGray(0); c.setLineWidth(0.6)
    c.setFont(fb, 8); c.setFillColorRGB(0.1, 0.45, 0.1)
    c.drawString(R - 229, sy - 12, "CHỮ KÝ SỐ MẪU - KHÔNG CÓ GIÁ TRỊ"); c.setFillGray(0)
    c.setFont(f, 7.5)
    c.drawString(R - 229, sy - 25, "Ký bởi: " + inv["ten_nguoi_ban"].upper()[:40])
    c.drawString(R - 229, sy - 36, "Ký ngày: " + inv["ngay_lap"])
    y = sy - 74
    if inv["ma_co_quan_thue"]:
        c.setFont(fb, 8); c.drawString(L, y, "Mã của cơ quan thuế: ")
        c.setFont(f, 8); c.drawString(L + 112, y, inv["ma_co_quan_thue"]); y -= 12
    c.setFont(f, 7.5)
    c.drawString(L, y, "Tra cứu tại Website (Search at): https://tracuuhoadon.example     Mã tra cứu (Invoice code): " + inv["ma_tra_cuu"]); y -= 11
    c.drawString(L, y, "(Cần kiểm tra, đối chiếu khi lập, giao, nhận hóa đơn)")
    c.setFont(f, 7); c.setFillGray(0.4)
    c.drawCentredString(W / 2, 24, "DỮ LIỆU GIẢ - CHỈ DÙNG THỬ NGHIỆM - KHÔNG PHẢI HÓA ĐƠN THẬT")
    c.showPage(); c.save()


def draw_pdf(inv, path):
    if inv["mau_trinh_bay"] == "P":
        return draw_portal(inv, path)
    W, H = A4
    c = canvas.Canvas(str(path), pagesize=A4)
    style = inv["mau_trinh_bay"]
    f, fb = ("VN", "VN-B") if style != "C" else ("VN-S", "VN-SB")
    left, right = 40, W - 40
    y = H - 50
    # tieu de nguoi ban
    if style == "B":
        c.setFont(fb, 12); c.drawCentredString(W / 2, y, inv["ten_nguoi_ban"].upper()); y -= 16
        c.setFont(f, 9); c.drawCentredString(W / 2, y, "Địa chỉ: " + inv["dia_chi_nguoi_ban"]); y -= 13
        c.drawCentredString(W / 2, y, "Mã số thuế: " + inv["mst_nguoi_ban"]); y -= 28
    else:
        c.setFont(fb, 11); c.drawString(left, y, inv["ten_nguoi_ban"]); y -= 14
        c.setFont(f, 9); c.drawString(left, y, "Địa chỉ: " + inv["dia_chi_nguoi_ban"]); y -= 12
        c.drawString(left, y, "Mã số thuế: " + inv["mst_nguoi_ban"]); y -= 12
        c.drawString(left, y, "Điện thoại: 024 3xxx xxxx"); y -= 22
    c.setFont(fb, 16); c.drawCentredString(W / 2, y, "HÓA ĐƠN GIÁ TRỊ GIA TĂNG"); y -= 14
    c.setFont(f, 9); c.drawCentredString(W / 2, y, "(VAT INVOICE)"); y -= 12
    c.drawCentredString(W / 2, y, "Ngày " + inv["ngay_lap"].replace("/", " tháng ", 1).replace("/", " năm ", 1)); y -= 6
    ref_x = right - 150
    c.setFont(f, 9)
    c.drawString(ref_x, y + 20, "Mẫu số: " + inv["mau_so"])
    c.drawString(ref_x, y + 8, "Ký hiệu: " + inv["ky_hieu"])
    c.setFont(fb, 9); c.drawString(ref_x, y - 4, "Số: " + inv["so_hoa_don"])
    y -= 24
    # nguoi mua
    c.setFont(f, 9)
    for label, val in [("Họ tên người mua hàng: ", "(Mua tại quầy)"), ("Tên đơn vị: ", inv["ten_nguoi_mua"]),
                       ("Mã số thuế: ", inv["mst_nguoi_mua"]), ("Địa chỉ: ", inv["dia_chi_nguoi_mua"]),
                       ("Hình thức thanh toán: ", inv["hinh_thuc_tt"])]:
        c.drawString(left, y, label + val); y -= 13
    y -= 6
    # bang hang
    cols = [("STT", 28), ("Tên hàng hóa, dịch vụ", 210), ("ĐVT", 45), ("Số lượng", 55), ("Đơn giá", 80), ("Thành tiền", 97)]
    x0, rowh = left, 18
    c.setFillGray(0.88 if style != "B" else 0.95)
    c.rect(x0, y - rowh, sum(w for _, w in cols), rowh, fill=1, stroke=1)
    c.setFillGray(0); c.setFont(fb, 8.5)
    x = x0
    for name, w in cols:
        c.drawCentredString(x + w / 2, y - 12, name); x += w
    y -= rowh
    c.setFont(f, 8.5)
    for i, ln in enumerate(inv["dong_hang"], 1):
        vals = [str(i), ln["ten_hang"], ln["dvt"], fmt(ln["so_luong"]), fmt(ln["don_gia"]), fmt(ln["thanh_tien"])]
        x = x0
        for k, ((name, w), v) in enumerate(zip(cols, vals)):
            c.rect(x, y - rowh, w, rowh, fill=0, stroke=1)
            if k == 1:
                c.drawString(x + 4, y - 12, v)
            elif k >= 3:
                c.drawRightString(x + w - 4, y - 12, v)
            else:
                c.drawCentredString(x + w / 2, y - 12, v)
            x += w
        y -= rowh
    y -= 14
    tw = sum(w for _, w in cols)
    c.setFont(f, 9)
    rows = [("Cộng tiền hàng:", fmt(inv["tong_truoc_thue"])),
            (f"Thuế suất GTGT: {inv['thue_suat']}%      Tiền thuế GTGT:", fmt(inv["tien_thue"]))]
    for lab, val in rows:
        c.drawRightString(left + tw - 110, y, lab); c.drawRightString(left + tw - 4, y, val); y -= 14
    c.setFont(fb, 10)
    c.drawRightString(left + tw - 110, y, "Tổng cộng tiền thanh toán:"); c.drawRightString(left + tw - 4, y, fmt(inv["tong_thanh_toan"])); y -= 18
    c.setFont(f, 9); c.drawString(left, y, "Số tiền viết bằng chữ: " + inv["bang_chu"]); y -= 40
    c.setFont(fb, 9); c.drawCentredString(left + 90, y, "Người mua hàng"); c.drawCentredString(right - 100, y, "Người bán hàng")
    c.setFont(f, 8); c.drawCentredString(right - 100, y - 12, "(Ký, đóng dấu, ghi rõ họ tên)")
    c.setFont(f, 7); c.setFillGray(0.45)
    c.drawCentredString(W / 2, 28, "DỮ LIỆU GIẢ - CHỈ DÙNG THỬ NGHIỆM - KHÔNG PHẢI HÓA ĐƠN THẬT")
    c.showPage(); c.save()


def draw_xml(inv, path):
    hh = "".join(
        f"<HHDVu><TChat>1</TChat><STT>{i}</STT><THHDVu>{escape(l['ten_hang'])}</THHDVu><DVTinh>{escape(l['dvt'])}</DVTinh>"
        f"<SLuong>{l['so_luong']}</SLuong><DGia>{l['don_gia']}</DGia><ThTien>{l['thanh_tien']}</ThTien><TSuat>{inv['thue_suat']}%</TSuat></HHDVu>"
        for i, l in enumerate(inv["dong_hang"], 1))
    d, m, y = inv["ngay_lap"].split("/")
    mcc = f"<MCCQT>{escape(inv['ma_co_quan_thue'])}</MCCQT>" if inv["ma_co_quan_thue"] else ""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- DU LIEU GIA, cau truc mo phong don gian hoa, chua kiem tra voi XSD chinh thuc -->
<HDon><DLHDon><TTChung><PBan>2.0.0</PBan><THDon>Hóa đơn giá trị gia tăng</THDon><KHMSHDon>{inv['mau_so']}</KHMSHDon><KHHDon>{inv['ky_hieu']}</KHHDon><SHDon>{int(inv['so_hoa_don'])}</SHDon><NLap>{y}-{m}-{d}</NLap><DVTTe>VND</DVTTe><HTTToan>{escape(inv['hinh_thuc_tt'])}</HTTToan></TTChung>
<NDHDon><NBan><Ten>{escape(inv['ten_nguoi_ban'])}</Ten><MST>{inv['mst_nguoi_ban']}</MST><DChi>{escape(inv['dia_chi_nguoi_ban'])}</DChi></NBan>
<NMua><Ten>{escape(inv['ten_nguoi_mua'])}</Ten><MST>{inv['mst_nguoi_mua']}</MST><DChi>{escape(inv['dia_chi_nguoi_mua'])}</DChi></NMua>
<DSHHDVu>{hh}</DSHHDVu>
<TToan><TgTCThue>{inv['tong_truoc_thue']}</TgTCThue><TgTThue>{inv['tien_thue']}</TgTThue><TgTTTBSo>{inv['tong_thanh_toan']}</TgTTTBSo><TgTTTBChu>{escape(inv['bang_chu'])}</TgTTTBChu></TToan></NDHDon></DLHDon>{mcc}</HDon>
"""
    Path(path).write_text(xml, encoding="utf-8")


def degrade(img, rng):
    """Mo phong anh chup dien thoai: nghieng, mo, nhieu, bong do, nen toi, nen JPEG."""
    img = img.convert("RGB")
    w, h = img.size
    bg = (rng.randint(150, 215),) * 3
    ang = rng.uniform(-4, 4)
    img = img.rotate(ang, expand=True, fillcolor=(255, 255, 255), resample=Image.BICUBIC)
    # canh nhin hoi lech (perspective nhe)
    w2, h2 = img.size
    s = rng.uniform(0.0, 0.05)
    coeffs = (1, s * rng.choice([-1, 1]), 0, 0, 1, 0, s / w2 * rng.choice([-1, 1]), 0)
    img = img.transform((w2, h2), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor=(255, 255, 255))
    canvas_img = Image.new("RGB", (w2 + 120, h2 + 120), bg)
    canvas_img.paste(img, (60, 60))
    a = np.asarray(canvas_img).astype(np.float32)
    # bong do dang gradient
    gx = np.linspace(rng.uniform(0.75, 1.0), rng.uniform(0.85, 1.05), a.shape[1])[None, :, None]
    gy = np.linspace(rng.uniform(0.8, 1.0), rng.uniform(0.9, 1.05), a.shape[0])[:, None, None]
    a *= gx * gy
    a += np.random.default_rng(rng.randint(0, 10**6)).normal(0, rng.uniform(3, 14), a.shape)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 1.6)))
    out = ImageEnhance.Contrast(out).enhance(rng.uniform(0.75, 1.1))
    out = ImageEnhance.Brightness(out).enhance(rng.uniform(0.8, 1.05))
    k = rng.choice([0.5, 0.65, 0.8])  # giam do phan giai
    out = out.resize((int(out.width * k), int(out.height * k)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--out", default="data_test")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--noisy-ratio", type=float, default=0.6, help="ti le anh bi lam nhieu")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--style", choices=["mix", "portal"], default="mix", help="portal: chi dung bo cuc hoa don dien tu song ngu")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    out = Path(a.out)
    for sub in ("pdf", "images", "xml"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    labels = []
    for i in range(1, a.n + 1):
        inv = make_invoice(rng, i, a.style)
        pdf = out / "pdf" / f"{inv['id']}.pdf"
        draw_pdf(inv, pdf)
        draw_xml(inv, out / "xml" / f"{inv['id']}.xml")
        base = out / "images" / f"{inv['id']}_clean"
        subprocess.run(["pdftoppm", "-png", "-r", str(a.dpi), "-singlefile", str(pdf), str(base)], check=True)
        noisy = rng.random() < a.noisy_ratio
        inv["anh"] = f"images/{inv['id']}.png"
        inv["lam_nhieu"] = noisy
        clean = Image.open(str(base) + ".png")
        (degrade(clean, rng) if noisy else clean).save(out / inv["anh"])
        Path(str(base) + ".png").unlink()
        labels.append(inv)
    (out / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(out / "labels.csv", "w", newline="", encoding="utf-8-sig") as fh:
        keys = ["id", "anh", "lam_nhieu", "so_hoa_don", "ky_hieu", "ngay_lap", "mst_nguoi_ban", "ten_nguoi_ban",
                "mst_nguoi_mua", "tong_truoc_thue", "thue_suat", "tien_thue", "tong_thanh_toan"]
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader(); w.writerows(labels)
    print(f"Da tao {a.n} hoa don trong {out}/ ({sum(l['lam_nhieu'] for l in labels)} anh lam nhieu)")


if __name__ == "__main__":
    main()
