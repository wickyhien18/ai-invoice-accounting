"""A6: OCR. PDF co lop chu thi doc thang; anh va PDF scan di qua PaddleOCR (tieng Viet).

Moi nguon (pymupdf words / PaddleOCR boxes) deu duoc gom thanh cac DONG theo toa do de nhan va gia tri
nam chung mot dong ("Tong tien thanh toan: 4.192.668"), la dang rule va LLM de doc nhat.
"""
import io
import logging
import os
import statistics
import threading
import time
from dataclasses import dataclass

from PIL import Image

from app.services.preprocess import preprocess

log = logging.getLogger(__name__)
_ENGINE = None


class OCRUnavailable(RuntimeError):
    """PaddleOCR chua cai hoac khong tai duoc mo hinh."""


class UnsupportedFile(ValueError):
    pass


@dataclass
class Item:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float  # 0..100


def group_rows(items: list[Item]) -> list[dict]:
    """Gom cac o chu thanh dong theo toa do y, sap xep trai->phai. Tra ve [{text, confidence, y}]."""
    items = [i for i in items if i.text.strip()]
    if not items:
        return []
    med_h = statistics.median(max(i.y1 - i.y0, 1.0) for i in items)
    items.sort(key=lambda i: ((i.y0 + i.y1) / 2, i.x0))
    rows: list[list[Item]] = []
    for it in items:
        yc = (it.y0 + it.y1) / 2
        if rows:
            cur = rows[-1]
            cy = statistics.mean((i.y0 + i.y1) / 2 for i in cur)
            if abs(yc - cy) <= 0.6 * med_h:
                cur.append(it)
                continue
        rows.append([it])
    out = []
    for r in rows:
        r.sort(key=lambda i: i.x0)
        out.append({"text": " ".join(i.text.strip() for i in r),
                    "confidence": round(sum(i.conf for i in r) / len(r), 1),
                    "y": round(statistics.mean((i.y0 + i.y1) / 2 for i in r), 1)})
    return out


_LOCK = threading.Lock()
_FAILED: tuple[float, str] | None = None
FAIL_TTL = 300  # giay: sau khi khoi tao loi, 5 phut sau moi thu lai (tranh moi anh deu cho tai mo hinh that bai)


def _engine():
    global _ENGINE, _FAILED
    if _ENGINE is not None:
        return _ENGINE
    with _LOCK:
        if _ENGINE is not None:
            return _ENGINE
        if _FAILED and time.time() - _FAILED[0] < FAIL_TTL:
            raise OCRUnavailable(_FAILED[1])
        try:
            try:
                from paddleocr import PaddleOCR
            except ImportError as e:
                raise OCRUnavailable("Chua cai paddleocr. Xem SETUP.md muc 3.1 (cai paddlepaddle truoc)") from e
            lang = os.getenv("OCR_LANG", "vi")
            try:
                try:
                    _ENGINE = PaddleOCR(lang=lang, use_angle_cls=True, show_log=False)   # 2.x
                except (TypeError, ValueError):
                    _ENGINE = PaddleOCR(lang=lang, use_textline_orientation=True)        # 3.x
            except OCRUnavailable:
                raise
            except Exception as e:  # tai mo hinh that bai (mang, dung luong...)
                raise OCRUnavailable(f"Khong khoi tao duoc PaddleOCR: {e}") from e
        except OCRUnavailable as e:
            _FAILED = (time.time(), str(e))
            raise
    return _ENGINE


def is_ready() -> bool:
    return _ENGINE is not None


def warmup() -> None:
    """Nap mo hinh luc khoi dong de anh dau tien khong phai cho. Loi chi ghi log, khong lam sap dich vu."""
    try:
        _engine()
        log.info("PaddleOCR san sang")
    except OCRUnavailable as e:
        log.warning("PaddleOCR chua dung duoc: %s", e)


def _poly_box(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def _paddle_items(img: Image.Image) -> list[Item]:
    import numpy as np
    eng = _engine()
    arr = np.asarray(img.convert("RGB"))
    items: list[Item] = []
    try:
        if hasattr(eng, "predict"):                   # PaddleOCR 3.x
            for res in eng.predict(arr):
                polys = res.get("rec_polys") if res.get("rec_polys") is not None else res.get("dt_polys")
                for t, s, poly in zip(res["rec_texts"], res["rec_scores"], polys):
                    items.append(Item(t, *_poly_box(poly), float(s) * 100))
        else:                                          # PaddleOCR 2.x
            for page in eng.ocr(arr, cls=True) or []:
                for poly, (t, s) in page or []:
                    items.append(Item(t, *_poly_box(poly), float(s) * 100))
    except Exception as e:
        raise OCRUnavailable(f"PaddleOCR loi khi doc anh: {e}") from e
    return items


def ocr_image(img: Image.Image, do_preprocess: bool = True) -> list[dict]:
    if do_preprocess:
        img = preprocess(img)
    return group_rows(_paddle_items(img))


def _pdf_rows(data: bytes, force_ocr: bool, do_preprocess: bool) -> tuple[list[dict], str]:
    import pymupdf
    doc = pymupdf.open(stream=data, filetype="pdf")
    rows: list[dict] = []
    source = "pdf_text"
    for page in doc:
        words = page.get_text("words")
        if not force_ocr and len(words) >= 20:
            rows += group_rows([Item(w[4], w[0], w[1], w[2], w[3], 100.0) for w in words])
        else:
            source = "ocr"
            img = Image.open(io.BytesIO(page.get_pixmap(dpi=200).tobytes("png")))
            rows += ocr_image(img, do_preprocess)
    return rows, source


def run_ocr(data: bytes, filename: str, force_ocr: bool = False, do_preprocess: bool = True) -> dict:
    name = filename.lower()
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        rows, source = _pdf_rows(data, force_ocr, do_preprocess)
    elif name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception as e:
            raise UnsupportedFile(f"Khong mo duoc anh: {e}") from e
        rows, source = ocr_image(img, do_preprocess), "ocr"
    else:
        raise UnsupportedFile("Chi nhan PDF, PNG, JPG")
    text = "\n".join(r["text"] for r in rows)
    avg = round(sum(r["confidence"] for r in rows) / len(rows), 1) if rows else 0.0
    return {"text": text, "lines": rows, "avg_confidence": avg, "source": source}
