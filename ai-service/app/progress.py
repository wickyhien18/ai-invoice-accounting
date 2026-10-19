"""Tien do xu ly tung tai lieu, giu trong bo nho (de giao dien hien thanh tien do).

POST /extract nhan job_id tuy chon va cap nhat o day qua tung buoc THAT (doc chu -> AI -> xong);
GET /progress/{job_id} tra ve buoc hien tai. Bo nho mat khi khoi dong lai dich vu (khong anh huong ket qua).
"""
import threading
import time

_TTL = 15 * 60
_jobs: dict[str, tuple[int, str, float]] = {}
_lock = threading.Lock()


def set_progress(job_id: str | None, percent: int, stage: str) -> None:
    if not job_id:
        return
    now = time.time()
    with _lock:
        for k in [k for k, v in _jobs.items() if now - v[2] > _TTL]:
            del _jobs[k]
        _jobs[job_id] = (percent, stage, now)


def get_progress(job_id: str) -> dict | None:
    with _lock:
        v = _jobs.get(job_id)
    return {"percent": v[0], "stage": v[1]} if v else None
