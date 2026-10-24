"""B5: goi y dinh khoan No/Co bang TF-IDF + Logistic Regression.

Dac trung (xem make_text): tu trong ten nguoi ban (bo dau), thue suat, khoang tien truoc thue, va cac to hop
"tu trong ten x khoang tien" de mo hinh bat duoc quy tac kieu "thiet bi IT tren 30 trieu -> TSCD (211)".
Hai bo phan loai rieng: tai khoan No (khoan muc chinh) va tai khoan Co. Do tin cay = P(No) * P(Co).
Dong thue GTGT (No 1331) do backend them theo quy tac, khong do mo hinh du doan.

Chay tu thu muc ai-service/:
    python -m app.services.gl_model train   # huan luyen tren data/gl_training.csv, luu models/
    python -m app.services.gl_model eval    # do tren tap kiem thu, in bang va ghi models/gl_metrics.json
Du lieu sinh bang `python tools/gen_gl_data.py` (du lieu GIA, xem docstring cua script do).
"""
import csv
import json
import logging
import os
import re
import statistics
import sys
import unicodedata
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "gl_training.csv"
MODEL_DIR = Path(os.getenv("GL_MODEL_DIR", ROOT / "models"))
MODEL_FILE = MODEL_DIR / "gl_model.joblib"
METRICS_FILE = MODEL_DIR / "gl_metrics.json"

# Bien gioi khoang tien (dong): 3 trieu va 30 trieu la nguong cong cu dung cu/TSCD thuong dung
BUCKETS = [1_000_000, 3_000_000, 10_000_000, 20_000_000, 30_000_000, 50_000_000, 100_000_000]
STOP = {"cong", "ty", "tnhh", "cp", "mtv", "doanh", "nghiep", "tu", "nhan", "mau", "thu", "va", "co", "phan"}
CONFIDENT = 0.6  # duoi muc nay (va la nguoi ban moi) thi hoi them LLM; tren nguong cung chi la uoc luong, xem bao cao muc 3


class ModelUnavailable(RuntimeError):
    """Chua co mo hinh va cung khong co du lieu de huan luyen."""


def strip_accents(s: str) -> str:
    s = s.replace("Đ", "D").replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def bucket(amount: float | None) -> str:
    if amount is None or amount <= 0:
        return "amt_none"
    for i, edge in enumerate(BUCKETS):
        if amount < edge:
            return f"amt_{i}"
    return f"amt_{len(BUCKETS)}"


def make_text(seller_name: str | None, vat_rate, total_before_tax) -> str:
    """Bien (ten nguoi ban, thue suat, tien truoc thue) thanh chuoi 'tu' de TF-IDF dem."""
    words = [w for w in re.findall(r"[a-z0-9]+", strip_accents((seller_name or "").lower())) if w not in STOP]
    try:
        amount = float(total_before_tax) if total_before_tax is not None else None
    except (TypeError, ValueError):
        amount = None
    b = bucket(amount)
    toks = list(words) + [f"{a}_{c}" for a, c in zip(words, words[1:])]
    toks += [f"{w}@{b}" for w in words]
    try:
        toks.append(f"vat_{int(float(vat_rate))}")
    except (TypeError, ValueError):
        toks.append("vat_none")
    toks.append(b)
    return " ".join(toks)


def _pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    return make_pipeline(
        TfidfVectorizer(token_pattern=r"\S+", lowercase=False, sublinear_tf=True),
        LogisticRegression(C=10.0, max_iter=3000),
    )


def load_rows(path: Path = DATA_FILE) -> list[dict]:
    if not path.is_file():
        raise ModelUnavailable(f"Không có dữ liệu huấn luyện {path}. Chạy: python tools/gen_gl_data.py")
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fit(rows: list[dict]) -> dict:
    X = [make_text(r["seller_name"], r["vat_rate"], r["total_before_tax"]) for r in rows]
    debit, credit = _pipeline(), _pipeline()
    debit.fit(X, [r["debit_account"] for r in rows])
    credit.fit(X, [r["credit_account"] for r in rows])
    return {"debit": debit, "credit": credit, "n_train": len(rows)}


def train(path: Path = DATA_FILE, out: Path = MODEL_FILE) -> dict:
    import joblib
    model = fit(load_rows(path))
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out)
    return model


_cache: dict | None = None


def get_model() -> dict:
    """Doc mo hinh da luu; hong/khac phien ban scikit-learn thi tu huan luyen lai tu du lieu."""
    global _cache
    if _cache is not None:
        return _cache
    import joblib
    if MODEL_FILE.is_file():
        try:
            _cache = joblib.load(MODEL_FILE)
            return _cache
        except Exception as e:  # khac phien ban sklearn, file hong...
            log.warning("Khong doc duoc %s (%s), huan luyen lai", MODEL_FILE, e)
    _cache = train()
    return _cache


def reset_cache() -> None:
    global _cache
    _cache = None


def _top(pipe, X: str, k: int = 3) -> list[tuple[str, float]]:
    proba = pipe.predict_proba([X])[0]
    order = sorted(range(len(proba)), key=lambda i: -proba[i])[:k]
    return [(str(pipe.classes_[i]), float(proba[i])) for i in order]


def predict(seller_name: str | None, vat_rate=None, total_before_tax=None) -> dict:
    m = get_model()
    X = make_text(seller_name, vat_rate, total_before_tax)
    d = _top(m["debit"], X)
    c = _top(m["credit"], X)
    return {
        "debit_account": d[0][0], "credit_account": c[0][0],
        "debit_probability": round(d[0][1], 4), "credit_probability": round(c[0][1], 4),
        "probability": round(d[0][1] * c[0][1], 4),
        "alternatives": [{"debit_account": a, "probability": round(p, 4)} for a, p in d[1:]],
    }


# --------------------------------------------------------------------------- danh gia (B9)
def _metrics(model: dict, rows: list[dict]) -> dict:
    n = len(rows)
    hit_d = hit_c = hit_both = conf_n = conf_hit = 0
    for r in rows:
        X = make_text(r["seller_name"], r["vat_rate"], r["total_before_tax"])
        (d, pd_), (c, pc) = _top(model["debit"], X, 1)[0], _top(model["credit"], X, 1)[0]
        ok_d, ok_c = d == r["debit_account"], c == r["credit_account"]
        hit_d += ok_d
        hit_c += ok_c
        hit_both += ok_d and ok_c
        if pd_ * pc >= CONFIDENT:
            conf_n += 1
            conf_hit += ok_d and ok_c
    return {"n_test": n, "debit_acc": hit_d / n, "credit_acc": hit_c / n, "pair_acc": hit_both / n,
            "confident_coverage": conf_n / n, "confident_pair_acc": (conf_hit / conf_n) if conf_n else None}


def _majority(train_rows: list[dict], test_rows: list[dict]) -> float:
    from collections import Counter
    best = Counter((r["debit_account"], r["credit_account"]) for r in train_rows).most_common(1)[0][0]
    return sum((r["debit_account"], r["credit_account"]) == best for r in test_rows) / len(test_rows)


def _history(train_rows: list[dict], test_rows: list[dict]) -> float | None:
    """Co so: 'nguoi ban nay lan truoc dinh khoan the nao thi lan nay the do' (chi dung duoc voi nguoi ban da thay)."""
    from collections import Counter, defaultdict
    seen: dict[str, Counter] = defaultdict(Counter)
    for r in train_rows:
        seen[r["mst_seller"]][(r["debit_account"], r["credit_account"])] += 1
    known = [r for r in test_rows if r["mst_seller"] in seen]
    if not known:
        return None
    ok = sum(seen[r["mst_seller"]].most_common(1)[0][0] == (r["debit_account"], r["credit_account"]) for r in known)
    return ok / len(known)


def _mean_sd(xs: list[float]) -> dict:
    xs = [x for x in xs if x is not None]
    return {"mean": statistics.mean(xs), "sd": statistics.pstdev(xs) if len(xs) > 1 else 0.0}


def evaluate(path: Path = DATA_FILE, repeats: int = 5) -> dict:
    """Hai cach chia tap, moi cach lap `repeats` lan voi hat giong khac nhau:
    - random: chia ngau nhien theo dong (nguoi ban co the xuat hien o ca huan luyen va kiem thu)
    - vendor_holdout: chia theo NGUOI BAN (kiem thu toan nguoi ban chua tung thay) -> sat voi "nguoi ban moi"
    """
    import random
    rows = load_rows(path)
    out: dict = {"n_rows": len(rows), "n_vendors": len({r["vendor_id"] for r in rows}), "repeats": repeats}
    for mode in ("random", "vendor_holdout"):
        runs, base, hist = [], [], []
        for seed in range(repeats):
            rng = random.Random(seed)
            if mode == "random":
                idx = list(range(len(rows)))
                rng.shuffle(idx)
                cut = int(len(idx) * 0.8)
                tr, te = [rows[i] for i in idx[:cut]], [rows[i] for i in idx[cut:]]
            else:
                vids = sorted({r["vendor_id"] for r in rows})
                rng.shuffle(vids)
                test_v = set(vids[: max(1, int(len(vids) * 0.2))])
                tr = [r for r in rows if r["vendor_id"] not in test_v]
                te = [r for r in rows if r["vendor_id"] in test_v]
            runs.append(_metrics(fit(tr), te))
            base.append(_majority(tr, te))
            hist.append(_history(tr, te))
        out[mode] = {k: _mean_sd([r[k] for r in runs]) for k in
                     ("debit_acc", "credit_acc", "pair_acc", "confident_coverage", "confident_pair_acc")}
        out[mode]["baseline_majority_pair_acc"] = _mean_sd(base)
        out[mode]["baseline_history_pair_acc"] = _mean_sd(hist) if any(h is not None for h in hist) else None
        out[mode]["n_test_avg"] = statistics.mean(r["n_test"] for r in runs)
    return out


def _pct(d: dict | None) -> str:
    return "—" if not d else f"{d['mean'] * 100:5.1f}% ± {d['sd'] * 100:.1f}"


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "train"
    if cmd == "train":
        m = train()
        print(f"Đã huấn luyện trên {m['n_train']} dòng -> {MODEL_FILE}")
    elif cmd == "eval":
        res = evaluate()
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        METRICS_FILE.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{res['n_rows']} dòng, {res['n_vendors']} người bán, lặp {res['repeats']} lần (trung bình ± độ lệch chuẩn)")
        for mode, title in (("random", "Chia ngẫu nhiên theo dòng"), ("vendor_holdout", "Chia theo người bán (người bán mới)")):
            r = res[mode]
            print(f"\n{title} (~{r['n_test_avg']:.0f} dòng kiểm thử/lần)")
            for key, label in (("debit_acc", "Đúng TK Nợ"), ("credit_acc", "Đúng TK Có"), ("pair_acc", "Đúng cả cặp Nợ+Có"),
                               ("baseline_majority_pair_acc", "Cơ sở: luôn chọn cặp phổ biến nhất"),
                               ("baseline_history_pair_acc", "Cơ sở: lặp lại lịch sử người bán"),
                               ("confident_coverage", f"Tỷ lệ dòng đủ tin cậy (≥{CONFIDENT})"),
                               ("confident_pair_acc", "Đúng cả cặp trong số dòng đủ tin cậy")):
                print(f"  {label:<44}{_pct(r[key])}")
        print(f"\nĐã ghi {METRICS_FILE}")
    else:
        sys.exit("Dùng: python -m app.services.gl_model [train|eval]")


if __name__ == "__main__":
    main(sys.argv)
