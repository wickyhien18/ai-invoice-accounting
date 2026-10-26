"""Ma hoa mat khau (bcrypt), JWT, va ham kiem tra quyen dung chung (Goi A - A2)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Invoice, User

ALGORITHM = "HS256"
bearer = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_access_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user.user_id), "role": user.role_name, "exp": exp},
                      settings.secret_key, algorithm=ALGORITHM)


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập hoặc phiên đã hết hạn")
    if cred is None:
        raise err
    try:
        payload = jwt.decode(cred.credentials, settings.secret_key, algorithms=[ALGORITHM])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise err
    if user is None:
        raise err
    return user


def work_roles() -> tuple[str, ...]:
    """Vai tro duoc tai/sua hoa don. Mac dinh chi KTV; KTT_CAN_WORK=1 (che do test) them KTT."""
    return ("KTV", "KTT") if settings.ktt_can_work else ("KTV",)


def require_worker(user: User = Depends(get_current_user)) -> User:
    """Cho endpoint tai hoa don: chi vai tro trong work_roles()."""
    if user.role_name not in work_roles():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Kế toán trưởng chỉ xem và duyệt, không tải hóa đơn")
    return user


def owned_invoice(invoice_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> Invoice:
    """Dung cho MOI endpoint SUA/GHI len mot hoa don: Depends(owned_invoice) (tham so duong dan phai ten invoice_id).

    Quy tac: hoa don cua ai thi nguoi do sua va chiu trach nhiem.
    - Chi KTV moi sua; KTT chi xem va duyet/tu choi (khong dung vao viec cua KTV).
    - KTV chi sua hoa don DO CHINH MINH tai len; hoa don cua KTV khac chi duoc xem.
    Tra ve hoa don de endpoint khoi phai truy van lai."""
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy hóa đơn")
    if user.role_name not in work_roles():
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Kế toán trưởng chỉ xem và duyệt, không chỉnh sửa hóa đơn của kế toán viên")
    if inv.uploaded_by != user.user_id:
        owner = db.get(User, inv.uploaded_by)
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            f"Hóa đơn này do {owner.full_name if owner else 'kế toán viên khác'} phụ trách, "
                            "chỉ người tải lên mới được chỉnh sửa")
    return inv


def require_role(*roles: str):
    """Dung: Depends(require_role("KTT")). Hien tai ho tro 2 vai tro: KTV, KTT."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role_name not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Không đủ quyền")
        return user
    return checker
