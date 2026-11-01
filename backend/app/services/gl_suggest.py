"""B6: gom cac nguon goi y dinh khoan theo thu tu tin cay giam dan, roi dung cac dong but toan.

    1. history - nguoi ban nay da duoc dinh khoan (hoa don da gui duyet/da duyet) -> lap lai cap hay dung nhat
    2. alias   - ten nguoi ban chua mot "cach viet khac" (category_aliases) cua mot loai khoan -> TK No mac dinh cua loai do
    3. ml/llm  - ai-service /classify-gl: TF-IDF + Logistic Regression, nguoi ban moi ma ML chua chac thi Gemini
    4. rule    - ai-service khong tra loi duoc: TK mac dinh 6422 / 331, ghi ro day chi la mac dinh

Moi dong tra ve co "source" de ke toan biet goi y den tu dau.
"""
import os
import re
import threading
import time
import unicodedata
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Account, CategoryAlias, Invoice, ItemCategory, JournalEntry
from app.services import gl_client

VAT_ACCOUNT = "1331"
DEFAULT_DEBIT, DEFAULT_CREDIT = "6422", "331"
# Tin dinh khoan da qua kiem tra cua ke toan vien ("da_luu") hoac da gui duyet: kiem tra hang loat thi hoa don sau
# cung nguoi ban voi hoa don truoc co ngay goi y tu lich su, khong phai hoi ML/Gemini lai
HISTORY_STATUSES = ("da_luu", "cho_duyet", "da_duyet")
# Khong dua cho Gemini chon: von/doanh thu/thu nhap/xac dinh ket qua va cac TK thue (thue do he thong tu them)
LLM_EXCLUDED_PREFIXES = ("133", "333", "4", "5", "7", "9", "821")
CENT = Decimal("0.01")

# Nho tam ket qua ai-service theo (nguoi ban, thue suat): hoa don cung nguoi ban trong mot lo khong phai goi ML/Gemini lai
# (Gemini ban mien phi gioi han so lan/phut nen goi lap lai la ly do goi y cham dan). Chi nho ket qua THANH CONG.
_ML_CACHE: dict[tuple, tuple[float, dict]] = {}
_ML_LOCK = threading.Lock()
ML_CACHE_TTL = 600.0   # giay
ML_CACHE_MAX = 500


def _cached_classify(payload: dict) -> dict | None:
    key = (fold(payload.get("seller_name")), payload.get("vat_rate"))
    now = time.monotonic()
    with _ML_LOCK:
        hit = _ML_CACHE.get(key)
        if hit and now - hit[0] < ML_CACHE_TTL:
            return dict(hit[1])
    ml = gl_client.classify_gl(payload)
    if ml and key[0] and not ml.get("llm_error"):   # Gemini loi/het luot: khong nho, lan sau thu lai
        with _ML_LOCK:
            if len(_ML_CACHE) >= ML_CACHE_MAX:
                _ML_CACHE.clear()
            _ML_CACHE[key] = (now, dict(ml))
    return ml


def fold(s: str | None) -> str:
    """Chu thuong, bo dau, bo ky tu la -> so khop alias khong phu thuoc dau/hoa thuong."""
    s = (s or "").replace("Đ", "D").replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


def money(d: Decimal) -> str:
    return format(d.quantize(CENT, ROUND_HALF_UP), "f")


def split_amounts(inv: Invoice) -> tuple[Decimal, Decimal]:
    """(tien truoc thue, tien thue). Thieu so lieu thi suy tu so con lai; khong suy duoc thi ValueError."""
    before, vat, total = inv.total_before_tax, inv.vat_amount, inv.total_amount
    if before is None and total is not None:
        before = total - (vat or Decimal(0))
    if before is None:
        raise ValueError("Hóa đơn chưa có số tiền để định khoản")
    if vat is None:
        vat = (total - before) if total is not None else Decimal(0)
    if before <= 0:
        raise ValueError("Tiền trước thuế phải lớn hơn 0")
    return before, max(vat, Decimal(0))


def history_pair(db: Session, inv: Invoice) -> tuple[tuple[str, str], int, int] | None:
    """(cap No/Co hay dung nhat, so lan, tong so lan) cua cung nguoi ban (MST, hoac ten neu khong co MST)."""
    if not (inv.mst_seller or inv.seller_name):
        return None
    same = Invoice.mst_seller == inv.mst_seller if inv.mst_seller else Invoice.seller_name == inv.seller_name
    rows = db.execute(
        select(JournalEntry.invoice_id, JournalEntry.debit_account, JournalEntry.credit_account)
        .join(Invoice, Invoice.invoice_id == JournalEntry.invoice_id)
        .where(same, Invoice.invoice_id != inv.invoice_id, Invoice.status.in_(HISTORY_STATUSES),
               JournalEntry.debit_account.notin_(("133", VAT_ACCOUNT)))).all()
    if not rows:
        return None
    # moi hoa don chi tinh MOT lan (dong dau tien khong phai thue) de hoa don nhieu dong khong "bo phieu" nhieu hon
    first: dict[int, tuple[str, str]] = {}
    for inv_id, d, c in rows:
        first.setdefault(inv_id, (d, c))
    top, n = Counter(first.values()).most_common(1)[0]
    return top, n, len(first)


def alias_category(db: Session, seller_name: str | None) -> ItemCategory | None:
    """Loai khoan co alias dai nhat nam trong ten nguoi ban va co TK No mac dinh."""
    name = fold(seller_name)
    if not name:
        return None
    best: tuple[int, ItemCategory] | None = None
    for alias, cat in db.execute(select(CategoryAlias.alias_text, ItemCategory)
                                 .join(ItemCategory, ItemCategory.category_id == CategoryAlias.category_id)
                                 .where(ItemCategory.default_debit_account.is_not(None))):
        a = fold(alias)
        if a and f" {a} " in f" {name} " and (best is None or len(a) > best[0]):
            best = (len(a), cat)
    return best[1] if best else None


def suggest(db: Session, inv: Invoice) -> dict:
    """Tra ve {"entries": [...], "warnings": [...]}. Nem ValueError neu thieu tien."""
    before, vat = split_amounts(inv)
    accounts = {a.account_code: a.account_name for a in db.scalars(select(Account))}
    warnings: list[str] = []
    main = None  # (debit, credit, source, probability, note)

    hist = history_pair(db, inv)
    if hist and all(a in accounts for a in hist[0]):
        (d, c), n, total = hist
        main = (d, c, "history", round(n / total, 4), f"Người bán này đã được định khoản như vậy {n}/{total} lần")

    if main is None:
        cat = alias_category(db, inv.seller_name)
        if cat and cat.default_debit_account in accounts and DEFAULT_CREDIT in accounts:
            main = (cat.default_debit_account, DEFAULT_CREDIT, "alias", None,
                    f"Tên người bán khớp loại khoản “{cat.category_name}”")

    if main is None:
        usable = [{"code": k, "name": v} for k, v in accounts.items() if not k.startswith(LLM_EXCLUDED_PREFIXES)]
        ml = _cached_classify({
            "seller_name": inv.seller_name, "vat_rate": float(inv.vat_rate) if inv.vat_rate is not None else None,
            "total_before_tax": float(before),
            # toi day nghia la khong co lich su -> nguoi ban moi. Gemini ban mien phi: 13 s/lan, ~18 lan/ngay DUNG CHUNG
            # voi buoc doc hoa don anh (llm.py), nen dat GL_USE_LLM=0 (backend/.env) de goi y chi dung ML (tuc thi), de danh
            # luot Gemini cho doc hoa don. Mac dinh 1 = giu hanh vi cu.
            "use_llm": os.getenv("GL_USE_LLM", "1").lower() not in ("0", "false", "no"),
            "accounts": usable,
        })
        if ml and ml.get("debit_account") in accounts and ml.get("credit_account") in accounts \
                and ml["debit_account"] != ml["credit_account"]:
            if ml.get("source") == "llm":
                main = (ml["debit_account"], ml["credit_account"], "llm", None,
                        "Người bán mới, mô hình thống kê chưa chắc nên hỏi Gemini: " + (ml.get("reason") or "không có giải thích"))
            else:
                p = ml.get("probability")
                note = "Mô hình thống kê (TF-IDF + hồi quy logistic) dự đoán theo tên người bán, thuế suất và số tiền"
                if ml.get("llm_error"):
                    note += f". Không hỏi được Gemini: {ml['llm_error']}"
                main = (ml["debit_account"], ml["credit_account"], "ml", p, note)
        else:
            if ml:
                warnings.append("Mô hình trả tài khoản không có trong danh mục của bạn, đã dùng mặc định")
            else:
                warnings.append("Dịch vụ AI không trả lời, đã dùng tài khoản mặc định")
            d, c = DEFAULT_DEBIT, DEFAULT_CREDIT
            main = (d, c, "rule", None, "Tài khoản mặc định (chi phí quản lý doanh nghiệp / phải trả người bán), cần kế toán xem lại")

    d, c, source, prob, note = main
    entries = [{"debit_account": d, "credit_account": c, "amount": money(before),
                "source": source, "probability": prob, "note": note}]
    if vat > 0:
        entries.append({"debit_account": VAT_ACCOUNT, "credit_account": c, "amount": money(vat), "source": "rule",
                        "probability": None, "note": "Thuế GTGT đầu vào được khấu trừ (mặc định coi là đủ điều kiện khấu trừ)"})
    for e in entries:
        for k in ("debit_account", "credit_account"):
            if e[k] not in accounts:
                warnings.append(f"Tài khoản {e[k]} chưa có trong danh mục tài khoản")
    if inv.total_amount is not None and abs(before + vat - inv.total_amount) > Decimal(1):
        warnings.append("Tổng các dòng định khoản khác tổng thanh toán trên hóa đơn; hãy kiểm tra lại các trường tiền")
    return {"entries": entries, "warnings": list(dict.fromkeys(warnings))}
