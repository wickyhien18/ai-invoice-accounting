"""B8 (Could): phan loai loai chung tu dau vao bang TF-IDF ky tu + Logistic Regression.

Dau vao la van ban OCR (hoac van ban doc tu PDF). Dung n-gram KY TU de chiu duoc loi OCR / mat dau.
Chay tu ai-service/:  python -m app.services.doc_model train|eval
Du lieu GIA, sinh bang tools/gen_gl_data.py: do chinh xac chi chung minh luong chay, khong dai dien chung tu that.
"""
import csv
import json
import logging
import os
import sys
from pathlib import Path

from app.services.gl_model import ModelUnavailable, strip_accents

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "doc_training.csv"
MODEL_DIR = Path(os.getenv("GL_MODEL_DIR", ROOT / "models"))
MODEL_FILE = MODEL_DIR / "doc_model.joblib"
METRICS_FILE = MODEL_DIR / "doc_metrics.json"

LABELS_VI = {
    "hoa_don_gtgt": "Hóa đơn GTGT", "hoa_don_ban_hang": "Hóa đơn bán hàng",
    "bien_lai_phieu_thu": "Biên lai / phiếu thu", "phieu_giao_hang_xuat_kho": "Phiếu giao hàng / xuất kho",
    "bao_gia_hop_dong": "Báo giá / hợp đồng", "khac": "Loại khác",
}
UNSURE = 0.5  # xac suat cao nhat thap hon muc nay thi tra "khac" kem co can_xem_lai


def _prep(text: str) -> str:
    return strip_accents((text or "").lower())


def _pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    return make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True, min_df=2),
                         LogisticRegression(C=20.0, max_iter=3000))


def load_rows(path: Path = DATA_FILE) -> list[dict]:
    if not path.is_file():
        raise ModelUnavailable(f"Không có dữ liệu huấn luyện {path}. Chạy: python tools/gen_gl_data.py")
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def train(path: Path = DATA_FILE, out: Path = MODEL_FILE):
    import joblib
    rows = load_rows(path)
    pipe = _pipeline().fit([_prep(r["text"]) for r in rows], [r["doc_type"] for r in rows])
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, out)
    return pipe


_cache = None


def get_model():
    global _cache
    if _cache is None:
        import joblib
        if MODEL_FILE.is_file():
            try:
                _cache = joblib.load(MODEL_FILE)
                return _cache
            except Exception as e:
                log.warning("Khong doc duoc %s (%s), huan luyen lai", MODEL_FILE, e)
        _cache = train()
    return _cache


def predict(text: str) -> dict:
    pipe = get_model()
    proba = pipe.predict_proba([_prep(text)])[0]
    order = sorted(range(len(proba)), key=lambda i: -proba[i])
    top = str(pipe.classes_[order[0]])
    p = float(proba[order[0]])
    unsure = p < UNSURE
    doc_type = "khac" if unsure else top
    return {"doc_type": doc_type, "label": LABELS_VI.get(doc_type, doc_type), "probability": round(p, 4),
            "can_xem_lai": unsure,
            "alternatives": [{"doc_type": str(pipe.classes_[i]), "probability": round(float(proba[i]), 4)}
                             for i in order[1:3]]}


def evaluate(path: Path = DATA_FILE, repeats: int = 5) -> dict:
    import random
    import statistics
    rows = load_rows(path)
    accs = []
    for seed in range(repeats):
        rng = random.Random(seed)
        idx = list(range(len(rows)))
        rng.shuffle(idx)
        cut = int(len(idx) * 0.8)
        tr, te = [rows[i] for i in idx[:cut]], [rows[i] for i in idx[cut:]]
        pipe = _pipeline().fit([_prep(r["text"]) for r in tr], [r["doc_type"] for r in tr])
        pred = pipe.predict([_prep(r["text"]) for r in te])
        accs.append(sum(p == r["doc_type"] for p, r in zip(pred, te)) / len(te))
    return {"n_rows": len(rows), "classes": sorted({r["doc_type"] for r in rows}), "repeats": repeats,
            "accuracy": {"mean": statistics.mean(accs), "sd": statistics.pstdev(accs)}}


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "train"
    if cmd == "train":
        train()
        print(f"Đã huấn luyện -> {MODEL_FILE}")
    elif cmd == "eval":
        r = evaluate()
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        METRICS_FILE.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        a = r["accuracy"]
        print(f"{r['n_rows']} mẫu, {len(r['classes'])} loại, lặp {r['repeats']} lần: đúng {a['mean']*100:.1f}% ± {a['sd']*100:.1f}")
    else:
        sys.exit("Dùng: python -m app.services.doc_model [train|eval]")


if __name__ == "__main__":
    main(sys.argv)
