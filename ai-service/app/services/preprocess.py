"""A6: tien xu ly anh truoc OCR bang Pillow (+ numpy): xoay thang, phong to, tang tuong phan, giam nhieu."""
import numpy as np
from PIL import Image, ImageFilter, ImageOps

MIN_SHORT_SIDE = 1400   # anh chup dien thoai bi giam do phan giai: phong to de chu du lon
MAX_LONG_SIDE = 3200    # tranh anh qua lon lam OCR cham


def _skew_angle(gray: Image.Image, limit: float = 6.0, step: float = 0.5) -> float:
    """Uoc luong goc nghieng bang phuong sai ham chieu ngang: dong chu thang thi phuong sai lon nhat."""
    small = gray.copy()
    small.thumbnail((700, 700))
    a = np.asarray(small)
    ink = Image.fromarray(((a < a.mean() * 0.8) * 255).astype("uint8"))  # chu = 255
    best, best_score = 0.0, -1.0
    angle = -limit
    while angle <= limit + 1e-9:
        rot = np.asarray(ink.rotate(angle, resample=Image.BILINEAR, fillcolor=0)) > 0
        score = float(np.var(rot.sum(axis=1)))
        if score > best_score:
            best, best_score = angle, score
        angle += step
    return best


def preprocess(img: Image.Image, deskew: bool = True) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    scale = 1.0
    if min(w, h) < MIN_SHORT_SIDE:
        scale = MIN_SHORT_SIDE / min(w, h)
    if max(w, h) * scale > MAX_LONG_SIDE:
        scale = MAX_LONG_SIDE / max(w, h)
    if abs(scale - 1) > 0.05:
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    gray = ImageOps.grayscale(img)
    if deskew:
        angle = _skew_angle(gray)
        if abs(angle) >= 0.5:
            img = img.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
            gray = ImageOps.grayscale(img)
    gray = gray.filter(ImageFilter.MedianFilter(3))               # giam nhieu hat
    gray = ImageOps.autocontrast(gray, cutoff=1)                  # keo gian tuong phan, giam bong do
    gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
    return gray.convert("RGB")                                    # PaddleOCR can 3 kenh
